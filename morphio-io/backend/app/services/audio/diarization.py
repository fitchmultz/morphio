"""
Speaker diarization service using pyannote-audio.

This module handles speaker diarization with subprocess isolation
to prevent memory conflicts between PyTorch and MLX on Apple Silicon.
The subprocess approach ensures that PyTorch's MPS backend doesn't
compete with MLX for Metal GPU memory.
"""

import asyncio
import json
import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from ...config import settings
from ...schemas.diarization_schema import DiarizationResult, SpeakerSegment

logger = logging.getLogger(__name__)

# Lazy-loaded pipeline to avoid import conflicts with MLX
_diarization_pipeline = None


def _load_pipeline():
    """
    Lazy-load the pyannote pipeline to avoid import conflicts with MLX.

    Only call this in the same-process path (use_subprocess=False).
    """
    global _diarization_pipeline
    if _diarization_pipeline is None:
        try:
            from pyannote.audio import Pipeline  # type: ignore[import-untyped]

            hf_token = settings.HUGGING_FACE_TOKEN.get_secret_value()
            if not hf_token:
                raise ValueError(
                    "HUGGING_FACE_TOKEN is required for pyannote-audio. "
                    "Get a token at https://huggingface.co/settings/tokens and "
                    "accept the model terms at https://huggingface.co/pyannote/speaker-diarization-3.1"
                )

            logger.info(f"Loading diarization model: {settings.DIARIZATION_MODEL}")
            loaded_pipeline = Pipeline.from_pretrained(settings.DIARIZATION_MODEL, token=hf_token)
            if loaded_pipeline is None:
                raise RuntimeError("Pipeline.from_pretrained returned None")

            # Move to MPS if available (Apple Silicon)
            import torch  # type: ignore[import-untyped]

            if torch.backends.mps.is_available():  # type: ignore[attr-defined]
                loaded_pipeline = loaded_pipeline.to(torch.device("mps"))  # type: ignore[attr-defined]
                logger.info("Diarization pipeline loaded on MPS (Apple Silicon GPU)")
            else:
                logger.info("Diarization pipeline loaded on CPU")

            _diarization_pipeline = loaded_pipeline

        except ImportError as e:
            logger.error(f"pyannote-audio not installed: {e}")
            raise

    return _diarization_pipeline


def _run_diarization_sync(
    audio_path: str,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
) -> DiarizationResult:
    """
    Synchronous diarization - runs in current process.

    WARNING: This can cause memory conflicts with MLX on Apple Silicon.
    Use subprocess isolation (default) unless you know what you're doing.
    """
    start_time = time.time()

    pipeline = _load_pipeline()
    if pipeline is None:
        raise RuntimeError("Failed to load diarization pipeline")

    # Build pipeline kwargs
    kwargs = {}
    if min_speakers is not None:
        kwargs["min_speakers"] = min_speakers
    if max_speakers is not None:
        kwargs["max_speakers"] = max_speakers

    # Run diarization
    diarization = pipeline(audio_path, **kwargs)

    # Convert to our schema
    segments = []
    speaker_set = set()

    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append(
            SpeakerSegment(
                speaker_id=speaker,
                start_time=turn.start,
                end_time=turn.end,
                confidence=None,  # pyannote doesn't provide per-segment confidence
            )
        )
        speaker_set.add(speaker)

    processing_time = time.time() - start_time
    logger.info(
        f"Diarization completed in {processing_time:.2f}s, "
        f"found {len(speaker_set)} speakers, {len(segments)} segments"
    )

    return DiarizationResult(
        segments=segments,
        num_speakers=len(speaker_set),
        processing_time_seconds=processing_time,
        model_name=settings.DIARIZATION_MODEL,
    )


# Subprocess script template for isolated diarization
_SUBPROCESS_SCRIPT = """
import json
import sys
import time

def main():
    start_time = time.time()

    audio_path = sys.argv[1]
    hf_token = sys.argv[2]
    min_speakers = int(sys.argv[3]) if sys.argv[3] != "None" else None
    max_speakers = int(sys.argv[4]) if sys.argv[4] != "None" else None
    model_name = sys.argv[5]

    from pyannote.audio import Pipeline
    import torch

    pipeline = Pipeline.from_pretrained(model_name, token=hf_token)

    if torch.backends.mps.is_available():
        pipeline = pipeline.to(torch.device("mps"))

    kwargs = {}
    if min_speakers is not None:
        kwargs["min_speakers"] = min_speakers
    if max_speakers is not None:
        kwargs["max_speakers"] = max_speakers

    diarization = pipeline(audio_path, **kwargs)

    segments = []
    speaker_set = set()

    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "speaker_id": speaker,
            "start_time": turn.start,
            "end_time": turn.end,
            "confidence": None
        })
        speaker_set.add(speaker)

    result = {
        "segments": segments,
        "num_speakers": len(speaker_set),
        "processing_time_seconds": time.time() - start_time,
        "model_name": model_name
    }

    print(json.dumps(result))

if __name__ == "__main__":
    main()
"""


def _run_diarization_subprocess(
    audio_path: str,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
) -> DiarizationResult:
    """
    Run diarization in a subprocess to isolate PyTorch memory from MLX.

    This prevents memory conflicts between the two frameworks on Apple Silicon
    by running PyTorch in a completely separate process.
    """
    # Create a temporary script file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(_SUBPROCESS_SCRIPT)
        script_path = f.name

    try:
        hf_token = settings.HUGGING_FACE_TOKEN.get_secret_value()
        if not hf_token:
            raise ValueError(
                "HUGGING_FACE_TOKEN is required for pyannote-audio. "
                "Get a token at https://huggingface.co/settings/tokens"
            )

        logger.info(f"Running diarization in subprocess for: {audio_path}")

        result = subprocess.run(
            [
                sys.executable,
                script_path,
                audio_path,
                hf_token,
                str(min_speakers),
                str(max_speakers),
                settings.DIARIZATION_MODEL,
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout for long audio
        )

        if result.returncode != 0:
            logger.error(f"Diarization subprocess failed: {result.stderr}")
            raise RuntimeError(f"Diarization failed: {result.stderr}")

        data = json.loads(result.stdout)

        logger.info(
            f"Subprocess diarization completed in {data['processing_time_seconds']:.2f}s, "
            f"found {data['num_speakers']} speakers"
        )

        return DiarizationResult(
            segments=[SpeakerSegment(**s) for s in data["segments"]],
            num_speakers=data["num_speakers"],
            processing_time_seconds=data["processing_time_seconds"],
            model_name=data["model_name"],
        )

    finally:
        # Clean up temporary script
        Path(script_path).unlink(missing_ok=True)


async def run_diarization(
    audio_path: str,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
    use_subprocess: Optional[bool] = None,
) -> DiarizationResult:
    """
    Run speaker diarization on an audio file.

    Args:
        audio_path: Path to the audio file
        min_speakers: Minimum expected number of speakers (optional hint)
        max_speakers: Maximum expected number of speakers (optional hint)
        use_subprocess: Whether to run in subprocess (default from settings)
                       Subprocess isolation prevents MLX/PyTorch memory conflicts.

    Returns:
        DiarizationResult with speaker segments

    Raises:
        ValueError: If HuggingFace token is not configured
        RuntimeError: If diarization fails
    """
    if use_subprocess is None:
        use_subprocess = settings.DIARIZATION_USE_SUBPROCESS

    # Use settings defaults if not provided
    min_spk = min_speakers if min_speakers is not None else settings.DIARIZATION_MIN_SPEAKERS
    max_spk = max_speakers if max_speakers is not None else settings.DIARIZATION_MAX_SPEAKERS

    if use_subprocess:
        return await asyncio.to_thread(_run_diarization_subprocess, audio_path, min_spk, max_spk)
    else:
        return await asyncio.to_thread(_run_diarization_sync, audio_path, min_spk, max_spk)


def is_diarization_available() -> bool:
    """
    Check if diarization is available (enabled and token configured).

    Returns:
        True if diarization can be used, False otherwise
    """
    if not settings.DIARIZATION_ENABLED:
        return False

    hf_token = settings.HUGGING_FACE_TOKEN.get_secret_value()
    if not hf_token:
        logger.warning("Diarization enabled but HUGGING_FACE_TOKEN not configured")
        return False

    return True
