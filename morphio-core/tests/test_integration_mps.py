"""Integration tests for MPS (Metal Performance Shaders) detection on Apple Silicon.

These tests verify that on Apple Silicon Macs, the transcription module
correctly detects the hardware and uses Metal GPU acceleration when available.
"""

import platform
import sys

import pytest

from morphio_core.audio.transcription import (
    detect_optimal_backend,
    has_faster_whisper,
    has_mlx_whisper,
    is_apple_silicon,
)


class TestAppleSiliconDetection:
    """Tests for Apple Silicon hardware detection."""

    @pytest.mark.skipif(
        not (sys.platform == "darwin" and platform.machine() == "arm64"),
        reason="Only runs on Apple Silicon Macs",
    )
    def test_is_apple_silicon_detects_correctly(self):
        """On an Apple Silicon Mac, is_apple_silicon() must return True."""
        assert is_apple_silicon() is True

    @pytest.mark.skipif(
        sys.platform != "darwin" or platform.machine() != "arm64",
        reason="Only runs on Apple Silicon Macs",
    )
    def test_apple_silicon_detection_matches_platform(self):
        """Verify detection matches actual platform info."""
        expected = sys.platform == "darwin" and platform.machine() == "arm64"
        assert is_apple_silicon() == expected


class TestMPSBackendSelection:
    """Tests for MPS/Metal backend selection on Apple Silicon."""

    @pytest.mark.skipif(
        not (sys.platform == "darwin" and platform.machine() == "arm64"),
        reason="Only runs on Apple Silicon Macs",
    )
    @pytest.mark.skipif(
        not has_mlx_whisper(),
        reason="mlx-whisper not installed",
    )
    def test_mlx_backend_uses_metal_on_apple_silicon(self):
        """When mlx-whisper is available on Apple Silicon, it must use Metal."""
        backend, device = detect_optimal_backend()

        assert backend == "mlx", f"Expected mlx backend, got {backend}"
        assert device == "metal", f"Expected metal device (MPS), got {device}"

    @pytest.mark.skipif(
        not (sys.platform == "darwin" and platform.machine() == "arm64"),
        reason="Only runs on Apple Silicon Macs",
    )
    @pytest.mark.skipif(
        not has_mlx_whisper(),
        reason="mlx-whisper not installed",
    )
    def test_optimal_backend_prefers_mlx_over_faster_whisper(self):
        """On Apple Silicon with mlx-whisper, MLX should be preferred."""
        backend, device = detect_optimal_backend()

        # MLX should be chosen over faster-whisper on Apple Silicon
        assert backend == "mlx"
        # MLX on Apple Silicon should use Metal GPU
        assert device == "metal"


class TestMPSTranscriptionIntegration:
    """Integration tests for actual transcription using MPS."""

    @pytest.mark.skipif(
        not (sys.platform == "darwin" and platform.machine() == "arm64"),
        reason="Only runs on Apple Silicon Macs",
    )
    @pytest.mark.skipif(
        not has_mlx_whisper(),
        reason="mlx-whisper not installed",
    )
    def test_transcriber_reports_metal_device(self):
        """Transcriber should report using metal device on Apple Silicon."""
        from morphio_core.audio.transcription import Transcriber, TranscriptionConfig

        config = TranscriptionConfig(backend="mlx")
        transcriber = Transcriber(config=config)

        # Force backend initialization
        transcriber._ensure_backend()

        info = transcriber.backend_info
        assert info["backend"] == "mlx", f"Expected mlx backend, got {info['backend']}"
        assert info["device"] == "metal", f"Expected metal device, got {info['device']}"

    @pytest.mark.skipif(
        not (sys.platform == "darwin" and platform.machine() == "arm64"),
        reason="Only runs on Apple Silicon Macs",
    )
    @pytest.mark.skipif(
        not has_mlx_whisper(),
        reason="mlx-whisper not installed",
    )
    def test_auto_backend_selects_metal_on_apple_silicon(self):
        """Auto backend selection should use Metal on Apple Silicon."""
        from morphio_core.audio.transcription import Transcriber, TranscriptionConfig

        config = TranscriptionConfig(backend="auto")
        transcriber = Transcriber(config=config)

        # Force backend initialization
        transcriber._ensure_backend()

        info = transcriber.backend_info
        assert info["device"] == "metal", (
            f"Expected metal device for auto backend on Apple Silicon, got {info['device']}"
        )


class TestBackendAvailabilityDiagnostics:
    """Diagnostic tests that always run to report backend availability."""

    def test_report_hardware_detection_status(self):
        """Report current hardware detection status (diagnostic, always passes)."""
        is_as = is_apple_silicon()
        has_mlx = has_mlx_whisper()
        has_fw = has_faster_whisper()

        print("\n--- Hardware Detection Status ---")
        print(f"Platform: {sys.platform}")
        print(f"Machine: {platform.machine()}")
        print(f"is_apple_silicon(): {is_as}")
        print(f"has_mlx_whisper(): {has_mlx}")
        print(f"has_faster_whisper(): {has_fw}")

        if is_as:
            if has_mlx:
                print("Status: Apple Silicon with MLX - should use Metal (MPS)")
            elif has_fw:
                print("Status: Apple Silicon with faster-whisper - using CPU fallback")
                print("  Recommendation: Install mlx-whisper for GPU acceleration")
            else:
                print("Status: Apple Silicon but no backend installed")
                print("  Recommendation: Install mlx-whisper for optimal performance")

        # This test always passes - it's for diagnostic output
        assert True

    @pytest.mark.skipif(
        not (sys.platform == "darwin" and platform.machine() == "arm64"),
        reason="Only runs on Apple Silicon Macs",
    )
    def test_apple_silicon_should_have_mlx_whisper(self):
        """On Apple Silicon, mlx-whisper SHOULD be installed for GPU acceleration.

        This test will fail if mlx-whisper is not installed on Apple Silicon,
        serving as a reminder to install it for optimal performance.
        """
        assert has_mlx_whisper(), (
            "mlx-whisper is not installed on Apple Silicon. "
            "Install it with: uv add mlx-whisper\n"
            "This enables Metal GPU acceleration for significantly faster transcription."
        )
