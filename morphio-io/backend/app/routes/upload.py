import json
import re
import shutil
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from ..config import settings
from ..models.user import User
from ..services.security import get_current_user

router = APIRouter(tags=["Upload"])

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
TEMP_DIR = UPLOAD_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Maximum file size (100MB default, can be configured)
MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 100 * 1024 * 1024)
MAX_CHUNKS = 10000  # Reasonable maximum number of chunks

# Safe file_id pattern: alphanumeric, hyphens, underscores only (16-128 chars)
SAFE_FILE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{16,128}$")


def validate_file_id(file_id: str) -> str:
    """Validate file_id to prevent path traversal attacks."""
    if not file_id or not SAFE_FILE_ID_PATTERN.match(file_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid file_id format. Must be 16-128 alphanumeric characters, hyphens, or underscores.",
        )
    # Additional safety: ensure no path separators or special chars
    if ".." in file_id or "/" in file_id or "\\" in file_id or "\x00" in file_id:
        raise HTTPException(status_code=400, detail="Invalid file_id format")
    return file_id


def get_safe_path(base: Path, *parts: str) -> Path:
    """Construct a path and verify it stays within the base directory."""
    target = base.joinpath(*parts).resolve()
    base_resolved = base.resolve()
    if not str(target).startswith(str(base_resolved)):
        raise HTTPException(status_code=400, detail="Invalid path")
    return target


class CompleteUploadRequest(BaseModel):
    file_id: str

    @field_validator("file_id")
    @classmethod
    def validate_file_id_format(cls, v: str) -> str:
        if not v or not SAFE_FILE_ID_PATTERN.match(v):
            raise ValueError("Invalid file_id format")
        return v


@router.post("/chunk", operation_id="upload_chunk")
async def upload_chunk(
    chunk: UploadFile = File(...),
    metadata: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    try:
        meta = json.loads(metadata)

        # Validate and extract metadata fields
        file_id = validate_file_id(str(meta.get("file_id", "")))

        # Validate chunk_number as integer
        try:
            chunk_number = int(meta["chunk_number"])
            total_chunks = int(meta["total_chunks"])
        except (KeyError, ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid metadata: {e}")

        # Validate bounds
        if chunk_number < 0 or chunk_number >= MAX_CHUNKS:
            raise HTTPException(status_code=400, detail="Invalid chunk_number")
        if total_chunks < 1 or total_chunks > MAX_CHUNKS:
            raise HTTPException(status_code=400, detail="Invalid total_chunks")
        if chunk_number >= total_chunks:
            raise HTTPException(
                status_code=400, detail="chunk_number must be less than total_chunks"
            )

        # Namespace by user ID to prevent cross-user access
        user_temp_dir = get_safe_path(TEMP_DIR, str(current_user.id))
        user_temp_dir.mkdir(parents=True, exist_ok=True)

        file_temp_dir = get_safe_path(user_temp_dir, file_id)
        file_temp_dir.mkdir(exist_ok=True)

        # Use validated integer for chunk filename
        chunk_path = file_temp_dir / f"chunk_{chunk_number:05d}"

        # Read chunk data with size limit check
        chunk_data = await chunk.read()
        if len(chunk_data) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="Chunk too large")

        with chunk_path.open("wb") as f:
            f.write(chunk_data)

        # Save metadata on first chunk (includes user_id for verification)
        if chunk_number == 0:
            with (file_temp_dir / "metadata.json").open("w") as f:
                json.dump(
                    {
                        "total_chunks": total_chunks,
                        "user_id": current_user.id,
                    },
                    f,
                )

        return JSONResponse({"status": "success", "data": {}})
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete", operation_id="complete_upload")
async def complete_upload(
    request: CompleteUploadRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    try:
        # Validate file_id (already validated by Pydantic, but double-check)
        file_id = validate_file_id(request.file_id)

        # User-namespaced paths
        user_temp_dir = get_safe_path(TEMP_DIR, str(current_user.id))
        file_temp_dir = get_safe_path(user_temp_dir, file_id)

        if not file_temp_dir.exists():
            raise HTTPException(status_code=404, detail="Upload not found")

        # Load and verify metadata
        metadata_path = file_temp_dir / "metadata.json"
        if not metadata_path.exists():
            raise HTTPException(status_code=400, detail="Metadata missing")

        with metadata_path.open("r") as f:
            meta = json.load(f)
            total_chunks = int(meta["total_chunks"])
            # Verify ownership
            stored_user_id = meta.get("user_id")
            if stored_user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")

        # Get and sort chunks (use the zero-padded format)
        chunks = sorted(file_temp_dir.glob("chunk_*"), key=lambda x: int(x.name.split("_")[1]))

        # Validate chunk count
        if len(chunks) != total_chunks:
            raise HTTPException(
                status_code=400,
                detail=f"Expected {total_chunks} chunks, found {len(chunks)}",
            )

        # Store in user-specific directory with validated file_id
        user_upload_dir = get_safe_path(UPLOAD_DIR, str(current_user.id))
        user_upload_dir.mkdir(parents=True, exist_ok=True)

        final_path = get_safe_path(user_upload_dir, file_id)

        # Check total size before writing
        total_size = sum(chunk_path.stat().st_size for chunk_path in chunks)
        if total_size > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="Total file size exceeds limit")

        with final_path.open("wb") as outfile:
            for chunk_path in chunks:
                with chunk_path.open("rb") as infile:
                    shutil.copyfileobj(infile, outfile)

        def cleanup_temp_dir() -> None:
            shutil.rmtree(str(file_temp_dir), ignore_errors=True)

        background_tasks.add_task(cleanup_temp_dir)
        return JSONResponse(
            {
                "status": "success",
                "data": {"fileUrl": f"/uploads/{current_user.id}/{file_id}"},
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
