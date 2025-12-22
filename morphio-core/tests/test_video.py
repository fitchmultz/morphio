"""Tests for video processing module."""

import pytest

from morphio_core.exceptions import DownloadError, UnsupportedURLError
from morphio_core.video import (
    DownloadConfig,
    DownloadResult,
    detect_platform,
    extract_youtube_id,
    has_ytdlp,
    is_supported_url,
    is_valid_url,
    is_youtube_url,
    normalize_url,
)


class TestDetectPlatform:
    """Tests for platform detection."""

    def test_detect_youtube_standard(self):
        """Test detecting standard YouTube URLs."""
        assert detect_platform("https://youtube.com/watch?v=abc123") == "youtube"
        assert detect_platform("http://www.youtube.com/watch?v=abc123") == "youtube"

    def test_detect_youtube_short(self):
        """Test detecting YouTube short URLs."""
        assert detect_platform("https://youtu.be/abc123") == "youtube"

    def test_detect_youtube_shorts(self):
        """Test detecting YouTube Shorts URLs."""
        assert detect_platform("https://youtube.com/shorts/abc123") == "youtube"

    def test_detect_rumble(self):
        """Test detecting Rumble URLs."""
        assert detect_platform("https://rumble.com/v123abc") == "rumble"
        assert detect_platform("http://www.rumble.com/video") == "rumble"

    def test_detect_twitter(self):
        """Test detecting Twitter/X URLs."""
        assert detect_platform("https://twitter.com/user/status/123") == "twitter"
        assert detect_platform("https://x.com/user/status/123") == "twitter"

    def test_detect_tiktok(self):
        """Test detecting TikTok URLs."""
        assert detect_platform("https://tiktok.com/@user/video/123") == "tiktok"
        assert detect_platform("https://vm.tiktok.com/abc123") == "tiktok"

    def test_detect_unknown(self):
        """Test unknown platforms."""
        assert detect_platform("https://vimeo.com/123456") == "unknown"
        assert detect_platform("https://example.com/video.mp4") == "unknown"

    def test_detect_with_whitespace(self):
        """Test URLs with leading/trailing whitespace."""
        assert detect_platform("  https://youtube.com/watch?v=abc  ") == "youtube"


class TestIsSupportedUrl:
    """Tests for supported URL checking."""

    def test_supported_platforms(self):
        """Test that supported platforms return True."""
        assert is_supported_url("https://youtube.com/watch?v=abc123")
        assert is_supported_url("https://rumble.com/v123")
        assert is_supported_url("https://twitter.com/user/status/123")
        assert is_supported_url("https://tiktok.com/@user/video/123")

    def test_unsupported_platforms(self):
        """Test that unsupported platforms return False."""
        assert not is_supported_url("https://vimeo.com/123456")
        assert not is_supported_url("https://example.com/video.mp4")


class TestExtractYoutubeId:
    """Tests for YouTube ID extraction."""

    def test_standard_watch_url(self):
        """Test extracting from standard watch URL."""
        assert extract_youtube_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
        assert extract_youtube_id("http://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        """Test extracting from youtu.be URL."""
        assert extract_youtube_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        """Test extracting from Shorts URL."""
        assert extract_youtube_id("https://youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_live_url(self):
        """Test extracting from live URL."""
        assert extract_youtube_id("https://youtube.com/live/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_with_extra_params(self):
        """Test URLs with additional parameters."""
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ&t=30s&list=abc"
        assert extract_youtube_id(url) == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        """Test that invalid URLs return None."""
        assert extract_youtube_id("https://vimeo.com/123456") is None
        assert extract_youtube_id("not a url") is None

    def test_malformed_url_cleanup(self):
        """Test cleanup of malformed URLs."""
        # These can happen from double-paste errors
        url = "https://youtube.com/watch?v=https://youtube.com/watch?v=dQw4w9WgXcQ"
        result = extract_youtube_id(url)
        # Should extract an ID (may be the second one)
        assert result is not None
        assert len(result) == 11


class TestIsYoutubeUrl:
    """Tests for YouTube URL detection."""

    def test_youtube_urls(self):
        """Test YouTube URLs return True."""
        assert is_youtube_url("https://youtube.com/watch?v=abc123")
        assert is_youtube_url("https://youtu.be/abc123")
        assert is_youtube_url("https://www.youtube.com/shorts/abc123")

    def test_non_youtube_urls(self):
        """Test non-YouTube URLs return False."""
        assert not is_youtube_url("https://vimeo.com/123456")
        assert not is_youtube_url("https://rumble.com/v123")


class TestIsValidUrl:
    """Tests for general URL validation."""

    def test_valid_urls(self):
        """Test valid URLs return True."""
        assert is_valid_url("https://example.com/video.mp4")
        assert is_valid_url("http://localhost:8000/test")
        assert is_valid_url("ftp://files.example.com/data")

    def test_invalid_urls(self):
        """Test invalid URLs return False."""
        assert not is_valid_url("/path/to/file.mp4")
        assert not is_valid_url("not a url")
        assert not is_valid_url("")
        assert not is_valid_url("   ")


class TestNormalizeUrl:
    """Tests for URL normalization."""

    def test_add_scheme(self):
        """Test that scheme is added if missing."""
        assert normalize_url("youtube.com/watch?v=abc") == "https://youtube.com/watch?v=abc"
        assert normalize_url("www.youtube.com/watch?v=abc") == "https://www.youtube.com/watch?v=abc"

    def test_preserve_existing_scheme(self):
        """Test that existing scheme is preserved."""
        assert normalize_url("https://youtube.com/watch?v=abc") == "https://youtube.com/watch?v=abc"
        assert normalize_url("http://youtube.com/watch?v=abc") == "http://youtube.com/watch?v=abc"

    def test_strip_whitespace(self):
        """Test that whitespace is stripped."""
        assert normalize_url("  https://youtube.com/watch?v=abc  ") == "https://youtube.com/watch?v=abc"


class TestDownloadConfig:
    """Tests for DownloadConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DownloadConfig()
        assert config.no_playlist is True
        assert config.retries == 5
        assert config.concurrent_fragments == 16
        assert config.quiet is True
        assert config.verbose is False
        assert config.youtube_player_client == "android"

    def test_custom_config(self):
        """Test custom configuration."""
        config = DownloadConfig(
            retries=10,
            quiet=False,
            verbose=True,
        )
        assert config.retries == 10
        assert config.quiet is False
        assert config.verbose is True


class TestDownloadResult:
    """Tests for DownloadResult model."""

    def test_result_creation(self, tmp_path):
        """Test creating a download result."""
        result = DownloadResult(
            output_path=tmp_path / "video.mp4",
            title="Test Video",
            duration=120.5,
            format="bestaudio",
        )
        assert result.output_path == tmp_path / "video.mp4"
        assert result.title == "Test Video"
        assert result.duration == 120.5
        assert result.format == "bestaudio"

    def test_result_minimal(self, tmp_path):
        """Test result with only required fields."""
        result = DownloadResult(output_path=tmp_path / "video.mp4")
        assert result.output_path == tmp_path / "video.mp4"
        assert result.title is None
        assert result.duration is None


class TestHasYtdlp:
    """Tests for yt-dlp availability check."""

    def test_returns_bool(self):
        """Test that has_ytdlp returns a boolean."""
        result = has_ytdlp()
        assert isinstance(result, bool)


class TestExceptions:
    """Tests for video-related exceptions."""

    def test_unsupported_url_error(self):
        """Test UnsupportedURLError can be raised."""
        with pytest.raises(UnsupportedURLError):
            raise UnsupportedURLError("URL not supported")

    def test_download_error(self):
        """Test DownloadError can be raised."""
        with pytest.raises(DownloadError):
            raise DownloadError("Download failed")

    def test_exception_hierarchy(self):
        """Test exception hierarchy."""
        from morphio_core.exceptions import VideoProcessingError

        assert issubclass(UnsupportedURLError, VideoProcessingError)
        assert issubclass(DownloadError, VideoProcessingError)
