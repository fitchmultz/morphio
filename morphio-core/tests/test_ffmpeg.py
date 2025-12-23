"""
Tests for FFmpeg utilities.
"""

import shutil

import pytest

from morphio_core.exceptions import FFmpegError
from morphio_core.media import FFmpegConfig
from morphio_core.media.ffmpeg import (
    convert_to_audio,
    ensure_ffmpeg_available,
    probe_duration,
    run_ffmpeg,
)


class TestEnsureFFmpegAvailable:
    """Tests for ensure_ffmpeg_available."""

    def test_ffmpeg_available(self):
        """Test that FFmpeg check passes when installed."""
        if not shutil.which("ffmpeg"):
            pytest.skip("FFmpeg not installed")

        # Should not raise
        ensure_ffmpeg_available()

    def test_ffmpeg_error_message(self):
        """Test error message format for missing FFmpeg."""
        # We can't easily test the missing case, but we can verify the error class
        error = FFmpegError(
            message="FFmpeg not found",
            command=["ffmpeg"],
            stderr="command not found",
        )
        assert "FFmpeg not found" in str(error)
        assert "ffmpeg" in str(error)


class TestRunFFmpeg:
    """Tests for run_ffmpeg."""

    @pytest.mark.asyncio
    async def test_ffmpeg_version(self):
        """Test running FFmpeg with version flag."""
        if not shutil.which("ffmpeg"):
            pytest.skip("FFmpeg not installed")

        # -version should succeed
        stdout, stderr = await run_ffmpeg(["-version"])
        # Version info is in stderr for ffmpeg
        assert b"ffmpeg" in stdout.lower() or b"ffmpeg" in stderr.lower()

    @pytest.mark.asyncio
    async def test_ffmpeg_invalid_args(self):
        """Test that invalid FFmpeg args raise FFmpegError."""
        if not shutil.which("ffmpeg"):
            pytest.skip("FFmpeg not installed")

        with pytest.raises(FFmpegError) as exc_info:
            await run_ffmpeg(["-i", "/nonexistent/file.mp3", "/tmp/out.mp3"])

        assert exc_info.value.command is not None
        assert "/nonexistent/file.mp3" in " ".join(exc_info.value.command)


class TestProbeDuration:
    """Tests for probe_duration."""

    @pytest.mark.asyncio
    async def test_probe_nonexistent_file(self, tmp_path):
        """Test probing a nonexistent file raises FFmpegError."""
        if not shutil.which("ffprobe"):
            pytest.skip("ffprobe not installed")

        nonexistent = tmp_path / "nonexistent.mp3"

        with pytest.raises(FFmpegError):
            await probe_duration(nonexistent)


class TestConvertToAudio:
    """Tests for convert_to_audio."""

    @pytest.mark.asyncio
    async def test_convert_nonexistent_input(self, tmp_path):
        """Test converting nonexistent file raises FFmpegError."""
        if not shutil.which("ffmpeg"):
            pytest.skip("FFmpeg not installed")

        input_path = tmp_path / "nonexistent.mp4"
        output_path = tmp_path / "output.mp3"

        with pytest.raises(FFmpegError):
            await convert_to_audio(input_path, output_path)


class TestFFmpegError:
    """Tests for FFmpegError exception."""

    def test_error_with_all_fields(self):
        """Test FFmpegError with all fields populated."""
        error = FFmpegError(
            message="Conversion failed",
            command=["ffmpeg", "-i", "input.mp4", "output.mp3"],
            stderr="Error: codec not found",
        )

        error_str = str(error)
        assert "Conversion failed" in error_str
        assert "ffmpeg" in error_str
        assert "codec not found" in error_str

    def test_error_minimal(self):
        """Test FFmpegError with only message."""
        error = FFmpegError(message="Simple error")
        assert str(error) == "Simple error"

    def test_error_attributes(self):
        """Test FFmpegError attribute access."""
        error = FFmpegError(
            message="Test",
            command=["ffmpeg", "-version"],
            stderr="test stderr",
        )

        assert error.message == "Test"
        assert error.command == ["ffmpeg", "-version"]
        assert error.stderr == "test stderr"


class TestFFmpegConfig:
    """Tests for FFmpegConfig."""

    def test_default_config_auto_detects(self):
        """Test that default config uses auto-detection."""
        config = FFmpegConfig()
        assert config.ffmpeg_path is None
        assert config.ffprobe_path is None

    def test_custom_paths(self):
        """Test setting custom paths."""
        config = FFmpegConfig(
            ffmpeg_path="/opt/ffmpeg/bin/ffmpeg",
            ffprobe_path="/opt/ffmpeg/bin/ffprobe",
        )
        assert config.ffmpeg_path == "/opt/ffmpeg/bin/ffmpeg"
        assert config.ffprobe_path == "/opt/ffmpeg/bin/ffprobe"

    def test_get_ffmpeg_with_valid_custom_path(self):
        """Test get_ffmpeg works with valid custom path."""
        real_ffmpeg = shutil.which("ffmpeg")
        if not real_ffmpeg:
            pytest.skip("FFmpeg not installed")
        config = FFmpegConfig(ffmpeg_path=real_ffmpeg)
        assert config.get_ffmpeg() == real_ffmpeg

    def test_get_ffprobe_with_valid_custom_path(self):
        """Test get_ffprobe works with valid custom path."""
        real_ffprobe = shutil.which("ffprobe")
        if not real_ffprobe:
            pytest.skip("ffprobe not installed")
        config = FFmpegConfig(ffprobe_path=real_ffprobe)
        assert config.get_ffprobe() == real_ffprobe

    def test_get_ffmpeg_with_invalid_custom_path(self):
        """Test get_ffmpeg raises error for invalid custom path."""
        config = FFmpegConfig(ffmpeg_path="/nonexistent/ffmpeg")
        with pytest.raises(FFmpegError) as exc_info:
            config.get_ffmpeg()
        assert "not found or not executable" in str(exc_info.value)

    def test_get_ffprobe_with_invalid_custom_path(self):
        """Test get_ffprobe raises error for invalid custom path."""
        config = FFmpegConfig(ffprobe_path="/nonexistent/ffprobe")
        with pytest.raises(FFmpegError) as exc_info:
            config.get_ffprobe()
        assert "not found or not executable" in str(exc_info.value)

    def test_get_ffmpeg_auto_detect(self):
        """Test get_ffmpeg auto-detects when path not set."""
        if not shutil.which("ffmpeg"):
            pytest.skip("FFmpeg not installed")

        config = FFmpegConfig()
        ffmpeg = config.get_ffmpeg()
        assert ffmpeg is not None
        assert "ffmpeg" in ffmpeg

    def test_get_ffprobe_auto_detect(self):
        """Test get_ffprobe auto-detects when path not set."""
        if not shutil.which("ffprobe"):
            pytest.skip("ffprobe not installed")

        config = FFmpegConfig()
        ffprobe = config.get_ffprobe()
        assert ffprobe is not None
        assert "ffprobe" in ffprobe

    def test_config_is_frozen(self):
        """Test that FFmpegConfig is immutable."""
        config = FFmpegConfig()
        with pytest.raises(AttributeError):
            config.ffmpeg_path = "/new/path"  # type: ignore[misc]

    def test_ensure_ffmpeg_with_config(self):
        """Test ensure_ffmpeg_available accepts config."""
        if not shutil.which("ffmpeg"):
            pytest.skip("FFmpeg not installed")

        config = FFmpegConfig()
        # Should not raise
        ensure_ffmpeg_available(config=config)

    @pytest.mark.asyncio
    async def test_run_ffmpeg_with_config(self):
        """Test run_ffmpeg accepts config parameter."""
        if not shutil.which("ffmpeg"):
            pytest.skip("FFmpeg not installed")

        config = FFmpegConfig()
        stdout, stderr = await run_ffmpeg(["-version"], config=config)
        assert b"ffmpeg" in stdout.lower() or b"ffmpeg" in stderr.lower()

    @pytest.mark.asyncio
    async def test_probe_duration_with_config(self, tmp_path):
        """Test probe_duration accepts config parameter."""
        if not shutil.which("ffprobe"):
            pytest.skip("ffprobe not installed")

        # Test with nonexistent file (will raise, but verifies signature)
        config = FFmpegConfig()
        nonexistent = tmp_path / "nonexistent.mp3"

        with pytest.raises(FFmpegError):
            await probe_duration(nonexistent, config=config)

    @pytest.mark.asyncio
    async def test_convert_to_audio_with_config(self, tmp_path):
        """Test convert_to_audio accepts config parameter."""
        if not shutil.which("ffmpeg"):
            pytest.skip("FFmpeg not installed")

        config = FFmpegConfig()
        input_path = tmp_path / "nonexistent.mp4"
        output_path = tmp_path / "output.mp3"

        with pytest.raises(FFmpegError):
            await convert_to_audio(input_path, output_path, config=config)
