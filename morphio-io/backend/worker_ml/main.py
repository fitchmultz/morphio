import asyncio
import logging
import os

import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="Morphio ML Worker", version="1.0.0")


@app.get("/health/")
async def health() -> dict:
    return {"status": "ok"}


async def _transcribe(file_path: str, model_name: str) -> dict:
    """Transcribe audio using MLX (Apple Silicon) or Torch (Docker/Linux)."""
    use_mlx = os.environ.get("USE_MLX") == "1"

    if use_mlx:
        logger.info("Using MLX backend for transcription")
        try:
            import mlx_whisper

            result = await asyncio.to_thread(
                mlx_whisper.transcribe,
                file_path,
                path_or_hf_repo=f"mlx-community/whisper-{model_name}-mlx",
            )
            return {
                "text": result.get("text", ""),
                "segments": result.get("segments", []),
                "language": result.get("language", "en"),
            }
        except ImportError:
            raise ImportError("MLX deps not installed. Run: make install-native")
    else:
        logger.info("Using Torch backend for transcription")
        import whisper
        import torch

        def _device() -> str:
            try:
                if torch.cuda.is_available():
                    return "cuda"
                if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                    return "mps"
            except Exception:
                pass
            return "cpu"

        device = _device()
        model = await asyncio.to_thread(whisper.load_model, model_name)
        model = model.to(device)
        result = await asyncio.to_thread(model.transcribe, file_path)
        return {"text": result.get("text", ""), "confidence": result.get("confidence")}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)) -> JSONResponse:
    temp_path = f"/tmp/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        model = os.getenv("WHISPER_MODEL", "small")
        result = await _transcribe(temp_path, model)
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
