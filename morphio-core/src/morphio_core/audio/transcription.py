"""
Local Whisper transcription with hardware-optimized backends.

Backend Selection (auto mode):
1. Apple Silicon Mac -> MLX Whisper (uses Metal GPU, fastest on M-series)
2. NVIDIA GPU available -> faster-whisper with CUDA
3. Fallback -> faster-whisper on CPU

Dependencies (optional extras):
- mlx-whisper: For Apple Silicon
- faster-whisper: For NVIDIA GPU or CPU fallback
"""

import platform
import shutil
import sys
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ..exceptions import BackendNotAvailableError, TranscriptionError
from .types import (
    TranscriptionConfig,
    TranscriptionResult,
    TranscriptionSegment,
    WordTiming,
)

# --- Hardware Detection ---


def is_apple_silicon() -> bool:
    """Check if running on Apple Silicon Mac."""
    return sys.platform == "darwin" and platform.machine() == "arm64"


def has_nvidia_gpu() -> bool:
    """Check if NVIDIA GPU with CUDA is available for CTranslate2."""
    # CTranslate2-native check (faster-whisper's backend)
    try:
        import ctranslate2  # type: ignore[import-not-found]

        return "cuda" in ctranslate2.get_supported_compute_types("default")
    except (ImportError, Exception):
        pass

    # Fallback: check for nvidia-smi (indicates CUDA drivers present)
    return shutil.which("nvidia-smi") is not None


def has_mlx_whisper() -> bool:
    """Check if mlx-whisper is installed."""
    try:
        import mlx_whisper  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


def has_faster_whisper() -> bool:
    """Check if faster-whisper is installed."""
    try:
        import faster_whisper  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


def detect_optimal_backend() -> tuple[str, str]:
    """
    Detect the optimal backend and device for this system.

    Returns:
        Tuple of (backend_name, device_name)
        Device names: "metal" (Apple GPU), "cuda" (NVIDIA), "cpu"
    """
    if is_apple_silicon() and has_mlx_whisper():
        return ("mlx", "metal")  # Apple Metal GPU

    if has_faster_whisper():
        if has_nvidia_gpu():
            return ("faster-whisper", "cuda")
        return ("faster-whisper", "cpu")

    if has_mlx_whisper():
        # MLX can work on Intel Macs too, just slower
        return ("mlx", "cpu")

    raise BackendNotAvailableError(
        "No Whisper backend available. Install one of:\n"
        "  - mlx-whisper (Apple Silicon): uv add mlx-whisper\n"
        "  - faster-whisper (NVIDIA/CPU): uv add faster-whisper"
    )


# --- Backend Protocol ---


@runtime_checkable
class WhisperBackendProtocol(Protocol):
    """Protocol for Whisper backend implementations."""

    def transcribe(
        self,
        audio_path: Path,
        model: str,
        language: str | None,
        beam_size: int,
        word_timestamps: bool,
    ) -> TranscriptionResult: ...


# --- MLX Backend (Apple Silicon) ---


class MLXWhisperBackend:
    """MLX Whisper backend for Apple Silicon."""

    def __init__(self) -> None:
        try:
            import mlx_whisper  # type: ignore[import-not-found]

            self._mlx_whisper = mlx_whisper
        except ImportError as e:
            raise BackendNotAvailableError("mlx-whisper not installed") from e

    def transcribe(
        self,
        audio_path: Path,
        model: str,
        language: str | None,
        beam_size: int,
        word_timestamps: bool,
    ) -> TranscriptionResult:
        # MLX Whisper doesn't support beam search yet, force greedy decoding
        # beam_size=None triggers greedy decoder (not beam_size=1)
        result = self._mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=f"mlx-community/whisper-{model}-mlx",
            language=language,
            beam_size=None,  # Force greedy decoding (beam search not implemented)
            word_timestamps=word_timestamps,
        )

        return self._parse_result(result)

    def _parse_result(self, result: dict[str, Any]) -> TranscriptionResult:
        words: list[WordTiming] = []
        segments: list[TranscriptionSegment] = []

        for i, seg in enumerate(result.get("segments", [])):
            segments.append(
                TranscriptionSegment(
                    id=i,
                    text=seg["text"].strip(),
                    start_time=seg["start"],
                    end_time=seg["end"],
                )
            )

            # Words loop INSIDE segment loop - collect words from ALL segments
            for word_info in seg.get("words", []):
                words.append(
                    WordTiming(
                        word=word_info["word"].strip(),
                        start_time=word_info["start"],
                        end_time=word_info["end"],
                        confidence=word_info.get("probability"),
                    )
                )

        return TranscriptionResult(
            text=result["text"].strip(),
            language=result.get("language"),
            duration=segments[-1].end_time if segments else None,
            words=words,
            segments=segments,
            backend_used="mlx",
            device_used="metal" if is_apple_silicon() else "cpu",
        )


# --- Faster-Whisper Backend (NVIDIA/CPU) ---


class FasterWhisperBackend:
    """Faster-Whisper backend for NVIDIA GPU or CPU."""

    def __init__(self, device: str = "auto") -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]

            self._WhisperModel = WhisperModel
        except ImportError as e:
            raise BackendNotAvailableError("faster-whisper not installed") from e

        if device == "auto":
            self._device = "cuda" if has_nvidia_gpu() else "cpu"
        else:
            self._device = device

        self._compute_type = "float16" if self._device == "cuda" else "int8"
        self._models: dict[str, Any] = {}  # Cache loaded models

    def _get_model(self, model: str) -> Any:
        """Get or load a model (cached)."""
        if model not in self._models:
            self._models[model] = self._WhisperModel(
                model,
                device=self._device,
                compute_type=self._compute_type,
            )
        return self._models[model]

    def transcribe(
        self,
        audio_path: Path,
        model: str,
        language: str | None,
        beam_size: int,
        word_timestamps: bool,
    ) -> TranscriptionResult:
        whisper_model = self._get_model(model)

        segments_iter, info = whisper_model.transcribe(
            str(audio_path),
            language=language,
            beam_size=beam_size,
            word_timestamps=word_timestamps,
        )

        # Consume iterator
        segments_list = list(segments_iter)

        return self._parse_result(segments_list, info)

    def _parse_result(self, segments_list: list[Any], info: Any) -> TranscriptionResult:
        words: list[WordTiming] = []
        segments: list[TranscriptionSegment] = []
        full_text_parts: list[str] = []

        for i, seg in enumerate(segments_list):
            segments.append(
                TranscriptionSegment(
                    id=i,
                    text=seg.text.strip(),
                    start_time=seg.start,
                    end_time=seg.end,
                )
            )
            full_text_parts.append(seg.text.strip())

            if hasattr(seg, "words") and seg.words:
                for word_info in seg.words:
                    words.append(
                        WordTiming(
                            word=word_info.word.strip(),
                            start_time=word_info.start,
                            end_time=word_info.end,
                            confidence=getattr(word_info, "probability", None),
                        )
                    )

        return TranscriptionResult(
            text=" ".join(full_text_parts),
            language=info.language,
            duration=info.duration,
            words=words,
            segments=segments,
            backend_used="faster-whisper",
            device_used=self._device,
        )


# --- Main Transcriber Class ---


class Transcriber:
    """
    Local Whisper transcriber with automatic hardware optimization.

    Automatically selects the best backend:
    - Apple Silicon -> MLX Whisper (Metal GPU)
    - NVIDIA GPU -> faster-whisper (CUDA)
    - CPU fallback -> faster-whisper (CPU)
    """

    def __init__(self, config: TranscriptionConfig | None = None) -> None:
        self._config = config or TranscriptionConfig()
        self._backend: WhisperBackendProtocol | None = None
        self._backend_name: str | None = None
        self._device_name: str | None = None

    def _ensure_backend(self) -> WhisperBackendProtocol:
        """Initialize backend if needed."""
        if self._backend is not None:
            return self._backend

        cfg = self._config

        if cfg.backend == "auto":
            self._backend_name, self._device_name = detect_optimal_backend()
        elif cfg.backend == "mlx":
            self._backend_name = "mlx"
            self._device_name = "metal" if is_apple_silicon() else "cpu"
        else:  # faster-whisper
            self._backend_name = "faster-whisper"
            if cfg.device == "auto":
                self._device_name = "cuda" if has_nvidia_gpu() else "cpu"
            else:
                self._device_name = cfg.device

        # Create backend instance
        if self._backend_name == "mlx":
            self._backend = MLXWhisperBackend()
        else:
            self._backend = FasterWhisperBackend(device=self._device_name or "auto")

        return self._backend

    def transcribe(
        self,
        audio_path: str | Path,
        *,
        config: TranscriptionConfig | None = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio file using local Whisper.

        Args:
            audio_path: Path to audio file
            config: Optional config override for this call

        Returns:
            TranscriptionResult with text, words, and segments

        Raises:
            TranscriptionError: If transcription fails
            BackendNotAvailableError: If no backend is installed
        """
        cfg = config or self._config
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise TranscriptionError(f"Audio file not found: {audio_path}")

        backend = self._ensure_backend()

        try:
            return backend.transcribe(
                audio_path=audio_path,
                model=cfg.model,
                language=cfg.language,
                beam_size=cfg.beam_size,
                word_timestamps=cfg.word_timestamps,
            )
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}") from e

    @property
    def backend_info(self) -> dict[str, str | None]:
        """Get info about the active backend."""
        self._ensure_backend()
        return {
            "backend": self._backend_name,
            "device": self._device_name,
        }


# --- Convenience Function ---


def transcribe_audio(
    audio_path: str | Path,
    *,
    config: TranscriptionConfig | None = None,
) -> TranscriptionResult:
    """
    Transcribe audio file using local Whisper (hardware-optimized).

    Automatically selects the best backend for your hardware:
    - Apple Silicon Mac -> MLX Whisper (fastest)
    - NVIDIA GPU -> faster-whisper with CUDA
    - CPU -> faster-whisper

    Args:
        audio_path: Path to audio file
        config: Optional transcription configuration

    Returns:
        TranscriptionResult with text and timing information

    Example:
        # Basic transcription (auto-detect best backend)
        result = transcribe_audio("audio.mp3")
        print(result.text)
        print(f"Used: {result.backend_used} on {result.device_used}")

        # With specific model
        config = TranscriptionConfig(model="large-v3", language="en")
        result = transcribe_audio("audio.mp3", config=config)

        # Force specific backend
        config = TranscriptionConfig(backend="faster-whisper", device="cpu")
        result = transcribe_audio("audio.mp3", config=config)
    """
    transcriber = Transcriber(config=config)
    return transcriber.transcribe(audio_path)
