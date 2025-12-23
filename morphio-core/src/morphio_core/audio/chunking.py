"""
Audio file chunking using FFmpeg for efficient processing.

Provides both fast stream-copy segmentation and precise overlap-based chunking.
"""

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from ..exceptions import AudioChunkingError
from ..media.ffmpeg import FFmpegConfig, ensure_ffmpeg_available, probe_duration, run_ffmpeg
from .types import AudioChunk, ChunkingConfig, ChunkNamer, default_chunk_namer

# Codec mapping for output formats
OUTPUT_FORMAT_CODECS: dict[str, str] = {
    "mp3": "libmp3lame",
    "wav": "pcm_s16le",
    "m4a": "aac",
    "flac": "flac",
}


@dataclass
class ChunkingResult:
    """Result of audio chunking operation."""

    chunks: list[AudioChunk]
    total_duration: float
    original_file: Path


async def chunk_audio(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    config: ChunkingConfig | None = None,
    naming_strategy: ChunkNamer | None = None,
    ffmpeg_config: FFmpegConfig | None = None,
) -> ChunkingResult:
    """
    Chunk audio file into segments using FFmpeg.

    Args:
        input_path: Path to input audio file
        output_dir: Directory to write chunk files
        config: Optional chunking configuration
        naming_strategy: Optional callback for naming chunks
            Signature: (index: int, start: float, end: float) -> str
            If not provided, uses default_chunk_namer
        ffmpeg_config: Optional FFmpegConfig with custom binary paths

    Returns:
        ChunkingResult with list of AudioChunk objects

    Raises:
        FFmpegError: If FFmpeg command fails
        AudioChunkingError: If chunking logic fails

    Example:
        # With default naming
        result = await chunk_audio("audio.mp3", "/tmp/chunks")

        # With custom naming
        result = await chunk_audio(
            "audio.mp3",
            "/tmp/chunks",
            naming_strategy=lambda i, s, e: f"part_{i}.mp3"
        )

        # With custom FFmpeg path
        result = await chunk_audio(
            "audio.mp3",
            "/tmp/chunks",
            ffmpeg_config=FFmpegConfig(ffmpeg_path="/opt/ffmpeg/bin/ffmpeg"),
        )
    """
    ensure_ffmpeg_available(config=ffmpeg_config)

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = config or ChunkingConfig()
    namer = naming_strategy or default_chunk_namer

    if not input_path.exists():
        raise AudioChunkingError(f"Input file not found: {input_path}")

    # Get total duration
    total_duration = await probe_duration(input_path, config=ffmpeg_config)

    # Determine codec: copy (fast remux) or encode
    if cfg.copy_codec:
        codec_args = ["-acodec", "copy"]
    else:
        codec = OUTPUT_FORMAT_CODECS.get(cfg.output_format)
        if not codec:
            raise AudioChunkingError(f"Unknown output format: {cfg.output_format}")
        codec_args = ["-acodec", codec]

    # Calculate chunk boundaries
    overlap_sec = cfg.overlap_ms / 1000.0
    chunks: list[AudioChunk] = []
    index = 0
    start = 0.0

    while start < total_duration:
        end = min(start + cfg.segment_duration, total_duration)

        # Generate chunk filename
        filename = namer(index, start, end)
        chunk_path = output_dir / filename

        # Extract chunk with FFmpeg
        await run_ffmpeg(
            [
                "-i",
                str(input_path),
                "-ss",
                str(start),
                "-t",
                str(end - start),
                "-vn",  # No video
                *codec_args,
                str(chunk_path),
            ],
            config=ffmpeg_config,
        )

        chunks.append(
            AudioChunk(
                chunk_path=chunk_path,
                start_time=start,
                end_time=end,
            )
        )

        # Terminal condition: reached end of file
        if end >= total_duration:
            break

        # Advance start position with runtime safety check
        next_start = end - overlap_sec
        if next_start <= start:
            raise AudioChunkingError(
                f"Invalid chunking configuration: overlap ({overlap_sec}s) must be less than "
                f"segment_duration ({cfg.segment_duration}s) to ensure forward progress."
            )
        start = next_start
        index += 1

    return ChunkingResult(
        chunks=chunks,
        total_duration=total_duration,
        original_file=input_path,
    )


async def segment_audio_fast(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    segment_duration: int = 600,
    ffmpeg_config: FFmpegConfig | None = None,
) -> ChunkingResult:
    """
    Fast audio segmentation using stream copy (no re-encoding).

    This is faster than chunk_audio() but:
    - Doesn't support overlap
    - Requires input format to match output format
    - Cuts may not be frame-precise

    Args:
        input_path: Path to input audio file
        output_dir: Directory for output segments
        segment_duration: Segment length in seconds
        ffmpeg_config: Optional FFmpegConfig with custom binary paths

    Returns:
        ChunkingResult with list of AudioChunk objects

    Raises:
        FFmpegError: If FFmpeg command fails
    """
    ensure_ffmpeg_available(config=ffmpeg_config)

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise AudioChunkingError(f"Input file not found: {input_path}")

    file_base = input_path.stem
    file_ext = input_path.suffix or ".m4a"
    segment_pattern = str(output_dir / f"{file_base}_seg_%03d{file_ext}")

    # Use FFmpeg segment muxer for fast splitting
    await run_ffmpeg(
        [
            "-i",
            str(input_path),
            "-map",
            "0:a:0",
            "-c",
            "copy",
            "-f",
            "segment",
            "-segment_time",
            str(segment_duration),
            "-reset_timestamps",
            "1",
            segment_pattern,
        ],
        config=ffmpeg_config,
    )

    # Find generated segments and probe their durations
    import glob

    seg_paths = sorted(glob.glob(str(output_dir / f"{file_base}_seg_*{file_ext}")))

    chunks: list[AudioChunk] = []
    start = 0.0
    total_duration = 0.0

    for seg_path in seg_paths:
        dur = await probe_duration(Path(seg_path), config=ffmpeg_config)
        end = start + dur
        chunks.append(
            AudioChunk(
                chunk_path=Path(seg_path),
                start_time=start,
                end_time=end,
            )
        )
        start = end
        total_duration = end

    return ChunkingResult(
        chunks=chunks,
        total_duration=total_duration,
        original_file=input_path,
    )


@asynccontextmanager
async def audio_chunker(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    config: ChunkingConfig | None = None,
    naming_strategy: ChunkNamer | None = None,
    auto_cleanup: bool = True,
    ffmpeg_config: FFmpegConfig | None = None,
):
    """
    Context manager for audio chunking with automatic cleanup.

    Example:
        async with audio_chunker("audio.mp3", "/tmp/chunks") as result:
            for chunk in result.chunks:
                transcript = await transcribe(chunk.chunk_path)
        # Chunks automatically cleaned up on exit
    """
    result = await chunk_audio(
        input_path,
        output_dir,
        config=config,
        naming_strategy=naming_strategy,
        ffmpeg_config=ffmpeg_config,
    )

    try:
        yield result
    finally:
        if auto_cleanup:
            await cleanup_chunks(result.chunks)


async def cleanup_chunks(chunks: list[AudioChunk]) -> None:
    """Remove chunk files from disk."""
    import contextlib

    for chunk in chunks:
        with contextlib.suppress(OSError):
            os.remove(chunk.chunk_path)
