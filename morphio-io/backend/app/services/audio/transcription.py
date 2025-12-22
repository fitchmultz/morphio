import asyncio
import logging
import platform
import sys
from typing import List, Optional, Tuple

import httpx

try:
    import torch  # type: ignore[reportMissingImports]
except Exception:  # pragma: no cover
    torch = None  # type: ignore[assignment]

try:
    import whisper  # type: ignore[reportMissingImports]
except Exception:  # pragma: no cover
    whisper = None  # type: ignore[assignment]
from tenacity import retry, stop_after_attempt, wait_exponential

from ...config import settings
from ...schemas.audio_schema import (
    TranscriptionResult,
    TranscriptionSource,
    TranscriptionStatus,
)
from ...schemas.diarization_schema import WordTiming
from ...utils.cache_utils import (
    cache_transcription,
    get_cached_transcription,
    invalidate_cache,
)
from ...utils.file_utils import compute_file_hash

logger = logging.getLogger(__name__)


def get_device():
    if torch is not None:
        try:
            if torch.cuda.is_available():
                return "cuda"
            if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                return "mps"
        except Exception:
            pass
    return "cpu"


async def transcribe_audio_local(file_path: str, model_name: str = "small") -> TranscriptionResult:
    """Transcribe audio file using local Whisper model."""
    try:
        device = get_device()
        logger.info(f"Using device: {device}")

        # Prefer MLX on Apple Silicon regardless of torch.mps state
        is_apple_silicon = sys.platform == "darwin" and platform.machine() in {"arm64", "aarch64"}
        if is_apple_silicon:
            try:
                import mlx_whisper  # type: ignore[reportMissingImports]

                mlx_model = settings.WHISPER_MLX_MODEL or model_name
                repo = f"mlx-community/whisper-{mlx_model}-mlx"
                logger.info(f"Using MLX Whisper model '{mlx_model}' from '{repo}'")
                result = await asyncio.to_thread(
                    mlx_whisper.transcribe, file_path, path_or_hf_repo=repo
                )
            except ImportError:
                # Optional: Lightning Whisper MLX fallback if installed
                try:
                    from lightning_whisper_mlx import (  # type: ignore[reportMissingImports]
                        LightningWhisperMLX,
                    )

                    logger.info("Using LightningWhisperMLX backend")
                    lightning_whisper = LightningWhisperMLX(
                        model=model_name, batch_size=12, quant=None
                    )
                    result = await asyncio.to_thread(
                        lightning_whisper.transcribe, None, audio_path=file_path
                    )
                except ImportError:
                    logger.warning("MLX packages not available; falling back to CPU Whisper")
                    if whisper is None:
                        raise ImportError("Whisper module not available")
                    device = "cpu"
                    model = await asyncio.to_thread(whisper.load_model, model_name)
                    model = model.to(device)
                    result = await asyncio.to_thread(model.transcribe, file_path)
            except MemoryError as e:
                # Metal memory pressure - let outer @retry handle it
                logger.info(f"MLX memory pressure, will retry: {e}")
                raise
            except Exception as e:
                # Unknown MLX error - fallback to CPU
                logger.warning(f"MLX failed ({type(e).__name__}), using CPU: {e}")
                if whisper is None:
                    raise ImportError("Whisper module not available")
                device = "cpu"
                model = await asyncio.to_thread(whisper.load_model, model_name)
                model = model.to(device)
                result = await asyncio.to_thread(model.transcribe, file_path)
        else:
            # CUDA or CPU path using OpenAI Whisper
            if whisper is None:
                raise RuntimeError("whisper not installed in this environment")
            model = await asyncio.to_thread(whisper.load_model, model_name)
            model = model.to(device)
            try:
                result = await asyncio.to_thread(model.transcribe, file_path)
            except RuntimeError as e:
                # Handle MPS sparse op issues by retrying on CPU
                if "SparseMPS" in str(e) or "_sparse_coo_tensor" in str(e):
                    logger.warning("MPS op not supported during transcription; retrying on CPU")
                    model = await asyncio.to_thread(whisper.load_model, model_name)
                    model = model.to("cpu")
                    result = await asyncio.to_thread(model.transcribe, file_path)
                else:
                    raise

        if not result or not result.get("text"):
            logger.warning("Transcription result is empty or invalid")
            return TranscriptionResult(
                text="",
                confidence=None,
                status=TranscriptionStatus.FAILED,
                source=TranscriptionSource.WHISPER,
                error="Empty or invalid transcription result",
            )

        text_val = str(result.get("text", ""))
        conf_raw = result.get("confidence")
        conf_val = conf_raw if isinstance(conf_raw, (int, float)) else None
        return TranscriptionResult(
            text=text_val,
            confidence=conf_val,
            status=TranscriptionStatus.COMPLETED,
            source=TranscriptionSource.WHISPER,
            error=None,
        )

    except MemoryError:
        # Let MemoryError bubble up for @retry to handle
        raise
    except Exception as e:
        logger.error(f"Error in local transcription: {str(e)}", exc_info=True)
        return TranscriptionResult(
            text="",
            confidence=None,
            status=TranscriptionStatus.FAILED,
            source=TranscriptionSource.WHISPER,
            error=str(e),
        )


# Limit concurrent transcriptions to avoid GPU/MLX contention
try:
    import multiprocessing as _mp

    _cpu = _mp.cpu_count() or 4
except Exception:
    _cpu = 4

_SEM_SIZE = (
    1 if (sys.platform == "darwin" and platform.machine() in {"arm64", "aarch64"}) else min(2, _cpu)
)
_TRANSCRIBE_SEM = asyncio.Semaphore(_SEM_SIZE)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def transcribe_audio(
    file_path: str,
    source: TranscriptionSource = TranscriptionSource.WHISPER,
    identifier: Optional[str] = None,
) -> TranscriptionResult:
    """Transcribe audio file with caching."""
    try:
        cache_id = identifier or await compute_file_hash(file_path)
        cached_result = await get_cached_transcription(cache_id, source)
        if cached_result and cached_result.status == TranscriptionStatus.COMPLETED:
            logger.info(f"Using cached transcription for {cache_id}")
            return cached_result

        # Prefer external ML worker if configured
        if settings.WORKER_ML_URL:
            try:
                timeout = httpx.Timeout(settings.SERVICE_TIMEOUT)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    with open(file_path, "rb") as f:
                        files = {"file": (file_path.split("/")[-1], f, "audio/mpeg")}
                        resp = await client.post(
                            f"{settings.WORKER_ML_URL.rstrip('/')}/transcribe",
                            files=files,
                        )
                    resp.raise_for_status()
                    data = resp.json()
                    text = data.get("text", "")
                    if not text:
                        raise ValueError("Empty transcription from worker")
                    result = TranscriptionResult(
                        text=text,
                        confidence=data.get("confidence"),
                        status=TranscriptionStatus.COMPLETED,
                        source=source,
                        error=None,
                    )
            except Exception as e:
                logger.error(f"Remote ML worker error: {e}")
                # Fallback to local if available
                async with _TRANSCRIBE_SEM:
                    result = await transcribe_audio_local(file_path, settings.WHISPER_MODEL)
        else:
            async with _TRANSCRIBE_SEM:
                result = await transcribe_audio_local(file_path, settings.WHISPER_MODEL)
        if result.status == TranscriptionStatus.COMPLETED and result.text:
            await cache_transcription(cache_id, result, source)
            return result
        else:
            await invalidate_cache(f"{source.value}_transcription", cache_id)
            logger.error(f"Transcription failed for {file_path}: {result.error}")
            return result
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {e}", exc_info=True)
        error_result = TranscriptionResult(
            text="",
            confidence=None,
            status=TranscriptionStatus.FAILED,
            source=source,
            error=str(e),
        )
        if identifier:
            await invalidate_cache(f"{source.value}_transcription", identifier)
        return error_result


async def transcribe_audio_chunk(audio_chunk: str) -> str:
    """Transcribe a chunked audio file."""
    try:
        logger.debug(f"Transcribing chunk: {audio_chunk}")
        result = await transcribe_audio(audio_chunk)
        if not result or not result.text:
            logger.warning(f"Empty transcription for chunk: {audio_chunk}")
        return result.text if (result and result.text) else ""
    except Exception as e:
        logger.error(f"Error transcribing chunk {audio_chunk}: {str(e)}")
        return ""


async def transcribe_with_word_timestamps(
    file_path: str,
    model_name: str = "small",
) -> Tuple[str, List[WordTiming]]:
    """
    Transcribe audio file with word-level timestamps for diarization alignment.

    Uses MLX Whisper's word_timestamps feature on Apple Silicon,
    or OpenAI Whisper's word_timestamps on other platforms.

    Args:
        file_path: Path to the audio file
        model_name: Whisper model name (default: "small")

    Returns:
        Tuple of (transcribed text, list of word timings)
    """
    try:
        device = get_device()
        logger.info(f"Transcribing with word timestamps, device: {device}")

        is_apple_silicon = sys.platform == "darwin" and platform.machine() in {"arm64", "aarch64"}

        if is_apple_silicon:
            try:
                import mlx_whisper  # type: ignore[reportMissingImports]

                mlx_model = settings.WHISPER_MLX_MODEL or model_name
                repo = f"mlx-community/whisper-{mlx_model}-mlx"
                logger.info(f"Using MLX Whisper with word_timestamps from '{repo}'")

                result = await asyncio.to_thread(
                    mlx_whisper.transcribe,
                    file_path,
                    path_or_hf_repo=repo,
                    word_timestamps=True,
                )

            except ImportError:
                # Fallback to OpenAI Whisper on CPU
                logger.warning("MLX not available, using CPU Whisper with word_timestamps")
                if whisper is None:
                    raise ImportError("Whisper module not available")
                model = await asyncio.to_thread(whisper.load_model, model_name)
                model = model.to("cpu")
                result = await asyncio.to_thread(model.transcribe, file_path, word_timestamps=True)
        else:
            # CUDA or CPU path using OpenAI Whisper
            if whisper is None:
                raise RuntimeError("whisper not installed in this environment")
            model = await asyncio.to_thread(whisper.load_model, model_name)
            model = model.to(device)
            result = await asyncio.to_thread(model.transcribe, file_path, word_timestamps=True)

        if not result:
            logger.warning("Transcription result is empty")
            return "", []

        # Whisper returns a dict with text, segments, etc.
        if not isinstance(result, dict):
            logger.warning("Unexpected result type from transcription")
            return "", []

        text = str(result.get("text", ""))

        # Extract word timings from segments
        word_timings: List[WordTiming] = []
        segments = result.get("segments", [])
        if isinstance(segments, list):
            for segment in segments:
                if not isinstance(segment, dict):
                    continue
                words = segment.get("words", [])
                if not isinstance(words, list):
                    continue
                for word_info in words:
                    if not isinstance(word_info, dict):
                        continue
                    word_str = str(word_info.get("word", "")).strip()
                    if word_str:
                        start = word_info.get("start", 0.0)
                        end = word_info.get("end", 0.0)
                        prob = word_info.get("probability")
                        word_timings.append(
                            WordTiming(
                                word=word_str,
                                start_time=float(start) if start else 0.0,
                                end_time=float(end) if end else 0.0,
                                confidence=float(prob) if prob is not None else None,
                            )
                        )

        logger.info(f"Transcribed {len(word_timings)} words with timestamps")
        return text, word_timings

    except Exception as e:
        logger.error(f"Error in transcription with word timestamps: {e}", exc_info=True)
        return "", []


async def transcribe_chunk_with_timestamps(
    audio_chunk: str,
    chunk_offset: float = 0.0,
) -> Tuple[str, List[WordTiming]]:
    """
    Transcribe a chunk with word timestamps, adjusting times by chunk offset.

    Args:
        audio_chunk: Path to the audio chunk file
        chunk_offset: Time offset in seconds to add to all word timestamps

    Returns:
        Tuple of (transcribed text, list of word timings with adjusted times)
    """
    try:
        logger.debug(f"Transcribing chunk with timestamps: {audio_chunk}, offset: {chunk_offset}s")

        async with _TRANSCRIBE_SEM:
            text, word_timings = await transcribe_with_word_timestamps(
                audio_chunk, settings.WHISPER_MODEL
            )

        # Adjust timestamps by chunk offset
        if chunk_offset > 0:
            adjusted_timings = [
                WordTiming(
                    word=wt.word,
                    start_time=wt.start_time + chunk_offset,
                    end_time=wt.end_time + chunk_offset,
                    confidence=wt.confidence,
                )
                for wt in word_timings
            ]
            return text, adjusted_timings

        return text, word_timings

    except Exception as e:
        logger.error(f"Error transcribing chunk with timestamps: {e}")
        return "", []
