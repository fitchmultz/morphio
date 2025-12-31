import asyncio
import logging
import os
import time
import uuid

import uvicorn
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse

from worker_ml import model_cache

logger = logging.getLogger(__name__)

app = FastAPI(title="Morphio ML Worker", version="1.0.0")

_inference_semaphore: asyncio.Semaphore | None = None
_inference_limit: int | None = None


@app.get("/health/")
async def health() -> dict:
    return {"status": "ok"}


def _get_max_concurrency() -> int:
    raw = os.getenv("WORKER_ML_MAX_CONCURRENCY", "1")
    try:
        value = int(raw)
    except ValueError:
        value = 1
    return max(1, value)


def _get_inference_semaphore() -> asyncio.Semaphore:
    global _inference_semaphore, _inference_limit
    limit = _get_max_concurrency()
    if _inference_semaphore is None or _inference_limit != limit:
        _inference_semaphore = asyncio.Semaphore(limit)
        _inference_limit = limit
    return _inference_semaphore


def _reset_inference_semaphore() -> None:
    global _inference_semaphore, _inference_limit
    _inference_semaphore = None
    _inference_limit = None


async def _transcribe(file_path: str, model_name: str, request_id: str | None = None) -> dict:
    """Transcribe audio using MLX (Apple Silicon) or Torch (Docker/Linux)."""
    use_mlx = os.environ.get("USE_MLX") == "1"
    backend_name = "MLX" if use_mlx else "Torch"
    logger.info("Using %s backend for transcription", backend_name)

    try:
        transcriber, model_load_ms = await model_cache.get_transcriber(model_name, use_mlx)
    except ImportError as exc:
        raise ImportError("MLX deps not installed. Run: make install-native") from exc

    semaphore = _get_inference_semaphore()
    max_concurrency = _get_max_concurrency()
    start = time.perf_counter()
    async with semaphore:
        result = await asyncio.to_thread(transcriber, file_path)
    transcribe_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "Transcription timing model_load_ms=%s transcribe_ms=%s max_concurrency=%s request_id=%s",
        model_load_ms,
        transcribe_ms,
        max_concurrency,
        request_id,
    )
    return result


@app.post("/transcribe")
async def transcribe(request: Request, file: UploadFile = File(...)) -> JSONResponse:
    temp_path = f"/tmp/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        model = os.getenv("WHISPER_MODEL", "small")
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        result = await _transcribe(temp_path, model, request_id=request_id)
        return JSONResponse({"status": "success", **result})
    except Exception as e:
        logger.exception("Transcription failed")
        return JSONResponse({"status": "error", "message": str(e), "text": ""}, status_code=500)
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass


if __name__ == "__main__":
    uvicorn.run("backend.worker_ml.main:app", host="0.0.0.0", port=8001)
