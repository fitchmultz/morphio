"""Audio file chunking using FFmpeg for efficient processing."""

import asyncio
import glob
import logging
import os
from typing import List

from ...schemas.audio_schema import (
    AudioChunk,
    AudioProcessingInput,
    AudioProcessingResult,
)
from ...utils.error_handlers import ApplicationException
from ...utils.file_utils import get_unique_filename

logger = logging.getLogger(__name__)


async def probe_audio_duration(file_path: str) -> float:
    """Get audio duration using ffprobe."""
    cmd_probe = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd_probe, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise ApplicationException(f"ffprobe failed: {err.decode('utf-8', 'ignore')}")
    return float(out.decode().strip())


async def segment_audio_fast(
    input_file: str,
    output_dir: str,
    segment_duration: int = 600,
) -> List[AudioChunk]:
    """
    Fast audio segmentation using stream copy (no re-encoding).

    Returns list of AudioChunk with timing info.
    """
    file_base = os.path.splitext(os.path.basename(input_file))[0]
    file_ext = os.path.splitext(input_file)[1].lower() or ".m4a"
    segment_pattern = os.path.join(output_dir, f"{file_base}_seg_%03d{file_ext}")

    cmd_seg = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        input_file,
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
    ]

    proc_seg = await asyncio.create_subprocess_exec(
        *cmd_seg, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, err_seg = await proc_seg.communicate()

    if proc_seg.returncode != 0:
        raise ApplicationException(
            f"ffmpeg segmentation failed: {err_seg.decode('utf-8', 'ignore')}"
        )

    seg_paths = sorted(glob.glob(os.path.join(output_dir, f"{file_base}_seg_*{file_ext}")))

    chunks = []
    start = 0.0
    for p in seg_paths:
        dur = await probe_audio_duration(p)
        end = start + dur
        chunks.append(AudioChunk(chunk_path=p, start_time=start, end_time=end))
        start = end

    return chunks


async def segment_audio_with_overlap(
    input_file: str,
    output_dir: str,
    chunk_duration: float = 600.0,
    overlap_ms: int = 2000,
    total_duration: float | None = None,
) -> List[AudioChunk]:
    """
    Segment audio with overlap for transcription continuity.

    Re-encodes to MP3 to ensure precise cuts.
    """
    if total_duration is None:
        total_duration = await probe_audio_duration(input_file)

    overlap_s = overlap_ms / 1000.0
    chunk_len_s = min(chunk_duration, total_duration)

    start = 0.0
    chunks = []
    file_base = os.path.splitext(os.path.basename(input_file))[0]

    while start < total_duration:
        end = min(start + chunk_len_s, total_duration)
        chunk_filename = f"{file_base}_{int(start)}_{int(end)}.mp3"
        chunk_path = get_unique_filename(output_dir, chunk_filename)

        cmd_chunk = [
            "ffmpeg",
            "-y",
            "-i",
            input_file,
            "-vn",
            "-acodec",
            "mp3",
            "-ss",
            str(start),
            "-t",
            str(end - start),
            chunk_path,
        ]

        proc_chunk = await asyncio.create_subprocess_exec(
            *cmd_chunk,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, err_chunk = await proc_chunk.communicate()

        if proc_chunk.returncode != 0:
            error_msg = err_chunk.decode("utf-8", errors="ignore").strip()
            logger.error(f"ffmpeg error for chunk: {error_msg}")
            raise ApplicationException(f"ffmpeg failed for chunk start={start} end={end}")

        chunks.append(AudioChunk(chunk_path=chunk_path, start_time=start, end_time=end))

        start = max(0, end - overlap_s)
        if end >= total_duration:
            break

    return chunks


async def chunk_audio_file(input_data: AudioProcessingInput) -> AudioProcessingResult:
    """
    Chunk audio file using ffmpeg.

    Tries fast path first (stream copy), falls back to overlap method.
    """
    original_file = input_data.file_path
    if not os.path.exists(original_file):
        raise ApplicationException(f"File not found: {original_file}")

    try:
        total_duration = await probe_audio_duration(original_file)
    except Exception as e:
        logger.error(f"Failed to probe audio duration: {e}")
        raise ApplicationException(f"Failed to get audio duration: {str(e)}", status_code=500)

    # Try fast path first
    try:
        chunks = await segment_audio_fast(
            original_file,
            input_data.output_directory,
            segment_duration=600,
        )
        if chunks:
            return AudioProcessingResult(
                original_file=original_file,
                processed_file=original_file,
                chunks=chunks,
                total_duration=total_duration,
            )
    except ApplicationException:
        pass  # Fall through to overlap method

    # Fallback to overlap method
    chunks = await segment_audio_with_overlap(
        original_file,
        input_data.output_directory,
        chunk_duration=600.0,
        overlap_ms=input_data.overlap_ms,
        total_duration=total_duration,
    )

    return AudioProcessingResult(
        original_file=original_file,
        processed_file=original_file,
        chunks=chunks,
        total_duration=total_duration,
    )


async def cleanup_chunks(chunk_paths: List[str]) -> None:
    """Clean up temporary chunk files."""
    for cp in chunk_paths:
        try:
            os.remove(cp)
        except OSError:
            pass
