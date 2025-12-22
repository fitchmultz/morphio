#!/usr/bin/env python3
"""
Universal Transcriber - Transcribe URLs or local files using MLX Whisper.

Accepts either a video/audio URL (YouTube, TikTok, X/Twitter, Rumble) or a local file path.
Uses the backend transcription service for reliable MLX GPU acceleration.

Usage:
    python transcribe.py <url_or_path> [options]

Examples:
    # Transcribe a TikTok video
    python transcribe.py "https://www.tiktok.com/@user/video/1234567890"

    # Transcribe a local video file
    python transcribe.py ~/Videos/interview.mp4

    # Save transcription to file
    python transcribe.py "https://youtu.be/VIDEO_ID" -o transcript.txt

    # Use a different Whisper model
    python transcribe.py video.mp4 --model medium
"""

import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# --- URL Detection ---

URL_PATTERNS = {
    "youtube": r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/.+",
    "tiktok": r"(?:https?://)?(?:www\.)?(?:vm\.)?tiktok\.com/.+",
    "x": r"(?:https?://)?(?:www\.)?(?:x\.com|twitter\.com)/.+",
    "rumble": r"(?:https?://)?(?:www\.)?rumble\.com/.+",
}


def detect_platform(url: str) -> str | None:
    """Detect which platform a URL belongs to."""
    url = url.strip()
    for platform, pattern in URL_PATTERNS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return None


def is_url(input_str: str) -> bool:
    """Check if input looks like a URL."""
    return input_str.strip().startswith(("http://", "https://", "www."))


# --- Filename Utilities ---


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """Sanitize filename for safe filesystem usage."""
    if not filename:
        return "untitled"

    filename = str(filename).strip()
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    replacements = {
        "<": "(",
        ">": ")",
        ":": "-",
        '"': "'",
        "|": "-",
        "?": "",
        "*": "",
        "\\": "-",
        "/": "-",
        "\n": " ",
        "\r": " ",
        "\t": " ",
        "#": "hash",
        "@": "at",
    }
    for char, replacement in replacements.items():
        filename = filename.replace(char, replacement)

    filename = "".join(char for char in filename if ord(char) >= 32)
    filename = re.sub(r"[ -]+", " ", filename)
    filename = re.sub(r"[ ]{2,}", " ", filename)
    filename = filename.strip(". ")

    if not filename or filename.replace("_", "").replace("-", "").replace(" ", "").strip() == "":
        filename = "untitled"

    if len(filename) > max_length:
        truncated = filename[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.7:
            filename = truncated[:last_space]
        else:
            filename = truncated

    return filename


# --- Audio/Video Processing ---


def extract_audio(input_path: str, temp_dir: str) -> str:
    """Extract audio from video file using FFmpeg."""
    audio_path = os.path.join(temp_dir, "extracted_audio.wav")

    ffmpeg_cmd = [
        "ffmpeg",
        "-i",
        input_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-y",
        audio_path,
        "-loglevel",
        "error",
    ]

    logger.info("Extracting audio...")
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.warning(f"FFmpeg warning: {result.stderr}")
        return input_path

    if os.path.exists(audio_path):
        logger.info("Audio extracted successfully")
        return audio_path

    return input_path


async def download_video(url: str, temp_dir: str, platform: str) -> tuple[str, str, dict[str, Any]]:
    """Download video using yt-dlp."""
    if yt_dlp is None:
        logger.error("yt-dlp not installed. Install with: pip install yt-dlp")
        sys.exit(1)

    base_template = f"{platform}_%(id)s.%(ext)s"
    ydl_opts = {
        "format": "bestvideo*+bestaudio/best",
        "outtmpl": os.path.join(temp_dir, base_template),
        "writeinfojson": False,
        "extract_flat": False,
        "ignoreerrors": False,
        "no_warnings": True,
        "noplaylist": True,
    }

    # Platform-specific format preferences
    if platform == "tiktok":
        ydl_opts["format"] = "best[height<=720]/best"

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            title = info.get("title", "Unknown")
            return filename, title, info

    logger.info(f"Downloading {platform.upper()} video...")
    video_path, title, info = await asyncio.to_thread(_download)
    logger.info(f"Downloaded: {os.path.basename(video_path)}")
    return video_path, title, info


async def transcribe_with_diarization(
    audio_path: str, model_name: str
) -> tuple[str, list[dict], int]:
    """Transcribe with speaker diarization - CLI version."""
    from app.services.audio.diarization import run_diarization
    from app.services.audio.speaker_alignment import (
        align_speakers_to_words,
        format_diarized_transcript,
    )
    from app.services.audio.transcription import transcribe_with_word_timestamps

    # Run transcription with word timestamps
    logger.info("Transcribing with word timestamps...")
    text, word_timings = await transcribe_with_word_timestamps(audio_path, model_name)

    if not text:
        logger.error("Transcription failed")
        return "", [], 0

    # Run diarization
    logger.info("Running speaker diarization...")
    diarization_result = await run_diarization(audio_path)

    if not diarization_result or not diarization_result.segments:
        logger.warning("Diarization failed, returning plain transcription")
        return text, [], 0

    # Align speakers to words
    logger.info("Aligning speakers to transcript...")
    utterances = align_speakers_to_words(diarization_result, word_timings)

    # Format output
    diarized_text = format_diarized_transcript(utterances)

    # Convert to simple segment list for output
    segments = [
        {
            "speaker": u.speaker_id,
            "text": u.text,
            "start": u.start_time,
            "end": u.end_time,
        }
        for u in utterances
    ]

    logger.info(f"Diarization complete: {diarization_result.num_speakers} speakers detected")
    return diarized_text, segments, diarization_result.num_speakers


async def transcribe(
    audio_path: str, model_name: str, diarize: bool = False
) -> tuple[str, list | None, int]:
    """Transcribe audio, optionally with speaker diarization."""
    if diarize:
        return await transcribe_with_diarization(audio_path, model_name)

    # Existing path - plain transcription
    from app.services.audio.transcription import transcribe_audio_local

    logger.info(f"Transcribing with model '{model_name}' using MLX GPU...")
    result = await transcribe_audio_local(audio_path, model_name)

    if result.error:
        logger.error(f"Transcription error: {result.error}")
        return "", None, 0

    logger.info("Transcription complete")
    return result.text.strip() if result.text else "", None, 0


# --- Output Formatting ---


def format_markdown(
    video_info: dict,
    transcription: str,
    segments: list | None = None,
    num_speakers: int = 0,
) -> str:
    """Format video info and transcription as markdown."""
    title = video_info.get("title", "Unknown Title")
    uploader = video_info.get("uploader", "Unknown")
    url = video_info.get("webpage_url", "")
    duration_raw = video_info.get("duration", 0)

    try:
        duration = int(duration_raw) if duration_raw else 0
    except (TypeError, ValueError):
        duration = 0

    if duration:
        minutes = duration // 60
        seconds = duration % 60
        duration_str = f"{minutes}:{seconds:02d}"
    else:
        duration_str = "Unknown"

    header = f"""# {title}

**User:** @{uploader}
**Duration:** {duration_str}
**URL:** {url}

"""

    if segments and num_speakers > 0:
        content = f"## Transcription ({num_speakers} speakers)\n\n"
        for seg in segments:
            content += f"**{seg['speaker']}**: {seg['text']}\n\n"
        return header + content
    else:
        return header + f"## Transcription\n\n{transcription}\n"


def save_transcription(
    text: str,
    output_path: Path,
    format_type: str,
    video_info: dict | None = None,
    segments: list | None = None,
    num_speakers: int = 0,
) -> str:
    """Save transcription to file."""
    if format_type == "txt":
        file_path = output_path.with_suffix(".txt")
        file_path.write_text(text, encoding="utf-8")

    elif format_type == "json":
        file_path = output_path.with_suffix(".json")
        data = {
            "title": video_info.get("title", "Unknown") if video_info else "Local File",
            "uploader": video_info.get("uploader", "Unknown") if video_info else None,
            "url": video_info.get("webpage_url", "") if video_info else None,
            "transcription": text,
            "word_count": len(text.split()),
            "character_count": len(text),
            "duration": video_info.get("duration", 0) if video_info else None,
        }
        if segments:
            data["segments"] = segments
            data["num_speakers"] = num_speakers
        file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    elif format_type == "md":
        file_path = output_path.with_suffix(".md")
        if video_info:
            content = format_markdown(video_info, text, segments, num_speakers)
        else:
            if segments and num_speakers > 0:
                content = f"# Transcription ({num_speakers} speakers)\n\n"
                for seg in segments:
                    content += f"**{seg['speaker']}**: {seg['text']}\n\n"
            else:
                content = f"# Transcription\n\n{text}\n"
        file_path.write_text(content, encoding="utf-8")

    else:
        raise ValueError(f"Unsupported format: {format_type}")

    return str(file_path)


# --- Main Entry Point ---


async def process_url(
    url: str, model: str, output: str | None, output_format: str, diarize: bool = False
) -> str:
    """Process a URL (download + transcribe)."""
    platform = detect_platform(url)
    if not platform:
        logger.error("Unsupported URL. Supported: YouTube, TikTok, X/Twitter, Rumble")
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="transcribe_") as temp_dir:
        video_path, title, video_info = await download_video(url, temp_dir, platform)
        audio_path = extract_audio(video_path, temp_dir)
        text, segments, num_speakers = await transcribe(audio_path, model, diarize)

        if not text:
            logger.error("No transcription generated")
            sys.exit(1)

        if output:
            output_path = Path(output)
            if output_path.suffix:
                # User specified extension, use it
                output_format = output_path.suffix[1:]  # Remove the dot
                output_path = output_path.with_suffix("")
            saved = save_transcription(
                text, output_path, output_format, video_info, segments, num_speakers
            )
            logger.info(f"Saved to: {saved}")
        else:
            # Print markdown to stdout
            print(format_markdown(video_info, text, segments, num_speakers))

        return text


async def process_file(
    file_path: str, model: str, output: str | None, output_format: str, diarize: bool = False
) -> str:
    """Process a local file."""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="transcribe_") as temp_dir:
        audio_path = extract_audio(file_path, temp_dir)
        text, segments, num_speakers = await transcribe(audio_path, model, diarize)

        if not text:
            logger.error("No transcription generated")
            sys.exit(1)

        if output:
            output_path = Path(output)
            if output_path.suffix:
                output_format = output_path.suffix[1:]
                output_path = output_path.with_suffix("")
            saved = save_transcription(
                text, output_path, output_format, None, segments, num_speakers
            )
            logger.info(f"Saved to: {saved}")
        else:
            # Print to stdout
            if segments and num_speakers > 0:
                print(f"\n{'=' * 60}")
                print(f"TRANSCRIPTION ({num_speakers} speakers):")
                print("=" * 60)
                print(text)
            else:
                print("\n" + "=" * 60)
                print("TRANSCRIPTION:")
                print("=" * 60)
                print(text)

        return text


async def main():
    parser = argparse.ArgumentParser(
        description="Transcribe URLs or local files using MLX Whisper GPU",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "https://www.tiktok.com/@user/video/123"
  %(prog)s ~/Videos/interview.mp4
  %(prog)s "https://youtu.be/VIDEO_ID" -o transcript.txt
  %(prog)s video.mp4 --model medium --format json
        """,
    )

    parser.add_argument("input", help="URL or file path to transcribe")
    parser.add_argument(
        "--model",
        "-m",
        default="small",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: small)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (default: print to stdout)",
    )
    parser.add_argument(
        "--format",
        "-f",
        default="md",
        choices=["md", "txt", "json"],
        help="Output format when saving (default: md)",
    )
    parser.add_argument(
        "--diarize",
        "-d",
        action="store_true",
        help="Enable speaker diarization (requires HuggingFace token)",
    )

    args = parser.parse_args()

    # Check diarization availability before processing
    if args.diarize:
        from app.services.audio.diarization import is_diarization_available

        if not is_diarization_available():
            logger.error("Diarization requires HUGGING_FACE_TOKEN. Set it in environment.")
            sys.exit(1)
        logger.info("Speaker diarization enabled (this may take several minutes for long audio)")

    if is_url(args.input):
        await process_url(args.input, args.model, args.output, args.format, args.diarize)
    else:
        await process_file(args.input, args.model, args.output, args.format, args.diarize)

    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(main())
