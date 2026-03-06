import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.job.status import get_job_status
from ..services.security import get_current_user
from ..utils.cache_utils import get_redis_client, is_redis_available
from ..utils.enums import JobStatus
from ..utils.error_handlers import ApplicationException

logger = logging.getLogger(__name__)

router = APIRouter()

TERMINAL_STATUSES = {
    JobStatus.COMPLETED.value,
    JobStatus.FAILED.value,
    JobStatus.CANCELLED.value,
}


def _extract_token(websocket: WebSocket) -> Optional[str]:
    token = websocket.query_params.get("token")
    if token:
        return token
    auth_header = websocket.headers.get("Authorization")
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return auth_header


def _normalize_status_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_id": payload.get("job_id"),
        "status": payload.get("status"),
        "progress": payload.get("progress"),
        "stage": payload.get("stage"),
        "message": payload.get("message"),
        "result": payload.get("result"),
        "error": payload.get("error"),
        "user_id": payload.get("user_id"),
    }


@router.websocket("/ws/job-status/{job_id}")
async def job_status_ws(
    websocket: WebSocket,
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    token = _extract_token(websocket)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        current_user = await get_current_user(token=token, db=db)
    except ApplicationException, Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        job_status = await get_job_status(job_id)
    except Exception as e:
        logger.warning(f"Failed to load job status for WebSocket {job_id}: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    if job_status.status == JobStatus.NOT_FOUND:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if job_status.user_id is None or job_status.user_id != current_user.id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    initial_payload = _normalize_status_payload(job_status.model_dump())
    await websocket.send_json(initial_payload)
    if initial_payload.get("status") in TERMINAL_STATUSES:
        await websocket.close()
        return

    if not is_redis_available():
        logger.warning("Redis not available for job status WebSocket streaming")
        await websocket.close()
        return

    channel = f"job_status:v1:{job_id}"
    client = get_redis_client()
    pubsub = client.pubsub()

    try:
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            raw_data = message.get("data")
            if isinstance(raw_data, (bytes, bytearray)):
                raw_data = raw_data.decode("utf-8", errors="ignore")
            payload: Optional[Dict[str, Any]] = None
            if isinstance(raw_data, str):
                try:
                    payload = json.loads(raw_data)
                except json.JSONDecodeError:
                    logger.warning("Discarding invalid job status payload from Redis")
                    continue
            elif isinstance(raw_data, dict):
                payload = raw_data

            if not payload:
                continue

            normalized = _normalize_status_payload(payload)
            await websocket.send_json(normalized)
            if normalized.get("status") in TERMINAL_STATUSES:
                await websocket.close()
                break
    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.warning(f"WebSocket streaming error for job {job_id}: {e}")
    finally:
        try:
            await pubsub.unsubscribe(channel)
        except Exception:
            pass
        await pubsub.close()
