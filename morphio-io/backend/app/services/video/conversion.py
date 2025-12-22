import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_ffmpeg_command(args: list[str]) -> None:
    """Run an ffmpeg command with the provided arguments."""
    cmd = ["ffmpeg", "-y"] + args
    logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        error = stderr.decode("utf-8", errors="replace")
        logger.error(f"FFmpeg error: {error}")
        raise RuntimeError(f"FFmpeg failed with exit code {proc.returncode}: {error}")


async def convert_video_to_audio_ffmpeg(video_path: str, audio_path: str) -> None:
    """Convert a video file to audio using ffmpeg."""
    try:
        args = [
            "-i",
            video_path,
            "-vn",  # No video
            "-acodec",
            "mp3",  # Use mp3 codec
            "-ab",
            "192k",  # 192kbps bitrate
            audio_path,
        ]
        await run_ffmpeg_command(args)
        logger.info(f"Successfully converted video to audio: {video_path} -> {audio_path}")
    except Exception as e:
        logger.error(f"Error converting video to audio: {e}")
        raise
