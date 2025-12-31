import asyncio
import importlib
import time
from typing import Callable, Optional, Tuple

_transcriber: Optional[Callable[[str], dict]] = None
_cache_key: Optional[Tuple[str, bool]] = None
_model_load_ms: Optional[int] = None
_load_lock = asyncio.Lock()


async def get_transcriber(
    model_name: str, use_mlx: bool
) -> Tuple[Callable[[str], dict], Optional[int]]:
    key = (model_name, use_mlx)
    if _transcriber is not None and _cache_key == key:
        return _transcriber, _model_load_ms

    async with _load_lock:
        if _transcriber is not None and _cache_key == key:
            return _transcriber, _model_load_ms
        start = time.perf_counter()
        transcriber = await _load_transcriber_impl(model_name, use_mlx)
        load_ms = int((time.perf_counter() - start) * 1000)
        _set_cache(transcriber, key, load_ms)
        return _transcriber, _model_load_ms


def get_model_load_ms() -> Optional[int]:
    return _model_load_ms


def reset_cache() -> None:
    _set_cache(None, None, None)


def _set_cache(
    transcriber: Optional[Callable[[str], dict]],
    key: Optional[Tuple[str, bool]],
    load_ms: Optional[int],
) -> None:
    global _transcriber, _cache_key, _model_load_ms
    _transcriber = transcriber
    _cache_key = key
    _model_load_ms = load_ms


async def _load_transcriber_impl(model_name: str, use_mlx: bool) -> Callable[[str], dict]:
    if use_mlx:
        mlx_whisper = importlib.import_module("mlx_whisper")
        repo = f"mlx-community/whisper-{model_name}-mlx"

        try:
            model = await asyncio.to_thread(mlx_whisper.load_model, repo)
        except AttributeError:
            model = None

        if model is not None and hasattr(model, "transcribe"):

            def _transcribe(file_path: str) -> dict:
                result = model.transcribe(file_path)
                return {
                    "text": result.get("text", ""),
                    "segments": result.get("segments", []),
                    "language": result.get("language", "en"),
                }

            return _transcribe

        def _transcribe(file_path: str) -> dict:
            result = mlx_whisper.transcribe(
                file_path,
                path_or_hf_repo=repo,
            )
            return {
                "text": result.get("text", ""),
                "segments": result.get("segments", []),
                "language": result.get("language", "en"),
            }

        return _transcribe

    whisper = importlib.import_module("whisper")
    torch = importlib.import_module("torch")

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

    def _transcribe(file_path: str) -> dict:
        result = model.transcribe(file_path)
        return {"text": result.get("text", ""), "confidence": result.get("confidence")}

    return _transcribe
