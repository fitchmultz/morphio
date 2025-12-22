"""Video processing types and configuration models."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DownloadResult(BaseModel):
    """Result of a video download operation."""

    model_config = ConfigDict(frozen=True)

    output_path: Path
    title: str | None = None
    duration: float | None = None
    format: str | None = None


class DownloadConfig(BaseModel):
    """Configuration for video downloading."""

    # Audio format preferences
    format_spec: str = Field(
        default="bestaudio[acodec*=opus]/251/bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
        description="yt-dlp format specification string",
    )
    # Output template (relative to output_dir)
    output_template: str = Field(
        default="%(id)s_%(title)s.%(ext)s",
        description="yt-dlp output template",
    )
    # Download behavior
    no_playlist: bool = Field(default=True, description="Don't download playlists")
    retries: int = Field(default=5, ge=0, description="Number of retries")
    concurrent_fragments: int = Field(default=16, ge=1, description="Concurrent fragment downloads")
    quiet: bool = Field(default=True, description="Suppress yt-dlp output")
    verbose: bool = Field(default=False, description="Verbose yt-dlp output")
    # YouTube-specific options
    youtube_player_client: str = Field(
        default="android",
        description="YouTube player client to use (helps avoid PO token issues)",
    )


# Supported video platforms
VideoPlatform = Literal["youtube", "rumble", "twitter", "tiktok", "unknown"]
