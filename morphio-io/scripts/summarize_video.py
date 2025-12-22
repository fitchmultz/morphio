#!/usr/bin/env python3
"""
Video Summarizer - Generate visual summaries with keyframes and chapters.

Transforms long-form videos (meetings, demos, courses) into skimmable
visual documents combining transcription, AI analysis, and keyframe screenshots.

Usage:
    python summarize_video.py <url_or_path> [options]

Examples:
    # Summarize a YouTube video with chapter breakdown
    python summarize_video.py "https://youtu.be/VIDEO_ID"

    # Local file with comprehensive analysis
    python summarize_video.py meeting.mp4 --verbosity comprehensive

    # Quick TL;DR without speaker detection
    python summarize_video.py lecture.mp4 --verbosity minimal --no-speakers

    # Output HTML to specific directory
    python summarize_video.py demo.mp4 --format html -o ~/summaries/
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Reuse existing transcribe.py utilities
from transcribe import (
    detect_platform,
    download_video,
    extract_audio,
    is_url,
    sanitize_filename,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Scene Detection ---


def detect_scenes(video_path: str, threshold: float = 30.0) -> list[tuple[float, float]]:
    """Detect scene boundaries using PySceneDetect.

    Returns list of (start_time, end_time) tuples in seconds.
    Falls back to fixed intervals if no scenes detected.
    """
    try:
        from scenedetect import ContentDetector, detect

        logger.info("Detecting scene boundaries...")
        scenes = detect(video_path, ContentDetector(threshold=threshold))

        if not scenes:
            logger.warning("No scene changes detected, using fixed intervals")
            return get_fixed_intervals(video_path)

        result = [(s.get_seconds(), e.get_seconds()) for s, e in scenes]
        logger.info(f"Detected {len(result)} scenes")
        return result

    except ImportError:
        logger.warning("scenedetect not available, using fixed intervals")
        return get_fixed_intervals(video_path)
    except Exception as e:
        logger.warning(f"Scene detection failed: {e}, using fixed intervals")
        return get_fixed_intervals(video_path)


def get_video_duration(video_path: str) -> float:
    """Get video duration using FFprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
    except Exception as e:
        logger.warning(f"Could not get duration: {e}")
    return 3600.0  # Default to 1 hour


def get_fixed_intervals(video_path: str, interval_seconds: float = 300.0) -> list[tuple[float, float]]:
    """Create fixed 5-minute intervals as fallback for scene detection."""
    duration = get_video_duration(video_path)
    intervals = []
    start = 0.0
    while start < duration:
        end = min(start + interval_seconds, duration)
        intervals.append((start, end))
        start = end
    return intervals


# --- Frame Extraction ---


async def extract_keyframes(
    video_path: str, scenes: list[tuple[float, float]], output_dir: str, max_frames: int = 30
) -> list[dict[str, Any]]:
    """Extract one keyframe per scene using FFmpeg.

    Args:
        video_path: Path to video file
        scenes: List of (start, end) time tuples
        output_dir: Directory to save frames
        max_frames: Maximum number of frames to extract

    Returns:
        List of dicts with timestamp, scene_index, and path
    """
    logger.info(f"Extracting keyframes from {len(scenes)} scenes...")
    frames = []

    # Limit to max_frames, evenly distributed across scenes
    if len(scenes) > max_frames:
        step = len(scenes) / max_frames
        scene_indices = [int(i * step) for i in range(max_frames)]
        selected_scenes = [(i, scenes[i]) for i in scene_indices]
    else:
        selected_scenes = list(enumerate(scenes))

    for i, (start, end) in selected_scenes:
        mid = start + (end - start) / 2
        frame_path = os.path.join(output_dir, f"frame_{i:04d}_{mid:.2f}.jpg")

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(mid),
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-q:v",
            "2",  # High quality JPEG
            "-vf",
            "scale='min(1280,iw)':'-1'",  # Max 1280px wide for token efficiency
            frame_path,
            "-loglevel",
            "error",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()

        if Path(frame_path).exists():
            frames.append({"timestamp": mid, "scene_index": i, "path": frame_path})

    logger.info(f"Extracted {len(frames)} keyframes")
    return frames


# --- Gemini Analysis ---

VERBOSITY_PROMPTS = {
    "minimal": """You are analyzing a video. Provide a 2-3 sentence TL;DR summary.
Focus on the main topic and key takeaway. Be concise.""",
    "chapter": """You are analyzing a video with keyframe images and transcript.
Create a chapter-based summary with this structure:

1. **Executive Summary** (3-4 sentences): What is this video about? Who is it for?

2. **Chapters**: For each major section:
   - Title (descriptive, 3-5 words)
   - Summary (2-3 sentences)
   - Key Points (3-5 bullet points)

Format as clean markdown. Reference specific moments when relevant.""",
    "comprehensive": """You are analyzing a video with keyframe images and transcript.
Provide comprehensive analysis with this structure:

1. **Executive Summary** (4-5 sentences)
   What is this video about? Why does it matter? Who should watch?

2. **Detailed Chapter Breakdown**
   For each major section:
   - Descriptive title
   - Full summary (paragraph)
   - Key points and quotes
   - Visual context from keyframes

3. **Key Insights**
   - Main takeaways
   - Action items (if applicable)
   - Notable quotes

4. **Audience & Use Cases**
   Who would benefit from this content and how?

Format as clean, readable markdown.""",
}


async def analyze_with_gemini(
    frames: list[dict],
    transcript: str,
    verbosity: str,
    speaker_info: str = "",
    title: str = "",
) -> dict[str, Any]:
    """Send frames + transcript to Gemini for multimodal analysis.

    Args:
        frames: List of frame dicts with 'path' key
        transcript: Full transcript text
        verbosity: One of 'minimal', 'chapter', 'comprehensive'
        speaker_info: Optional speaker diarization info
        title: Video title for context

    Returns:
        Dict with 'raw' response and parsed fields
    """
    from google import genai

    from app.config import settings

    api_key = settings.GEMINI_API_KEY.get_secret_value()
    if not api_key:
        logger.error("GEMINI_API_KEY not set. Please add it to your .env file.")
        return {"raw": transcript, "error": "No API key"}

    logger.info(f"Analyzing with Gemini ({verbosity} verbosity)...")

    client = genai.Client(api_key=api_key)

    # Build multimodal content: images first, then text
    contents = []

    # Add keyframe images (limit to 20 for token efficiency)
    frame_paths = [f["path"] for f in frames[:20]]
    for frame_path in frame_paths:
        try:
            with open(frame_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
            contents.append(
                {"inline_data": {"mime_type": "image/jpeg", "data": img_data}}
            )
        except Exception as e:
            logger.warning(f"Could not read frame {frame_path}: {e}")

    # Build prompt with context
    prompt_parts = [VERBOSITY_PROMPTS[verbosity]]

    if title:
        prompt_parts.append(f"\n**Video Title:** {title}")

    if speaker_info:
        prompt_parts.append(f"\n**Speakers:** {speaker_info}")

    # Truncate transcript if very long (Gemini has 1M context but let's be reasonable)
    max_transcript_chars = 100000  # ~25k tokens
    if len(transcript) > max_transcript_chars:
        transcript = transcript[:max_transcript_chars] + "\n\n[... transcript truncated ...]"

    prompt_parts.append(f"\n\n**Transcript:**\n{transcript}")

    contents.append("\n".join(prompt_parts))

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=contents,
        )
        return {"raw": response.text, "frames_analyzed": len(frame_paths)}

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return {"raw": transcript, "error": str(e)}


# --- Transcription ---


async def transcribe_video(audio_path: str, model_name: str) -> str:
    """Transcribe audio using existing MLX Whisper service."""
    from app.services.audio.transcription import transcribe_audio_local

    logger.info(f"Transcribing with MLX Whisper ({model_name})...")
    result = await transcribe_audio_local(audio_path, model_name)

    if result.error:
        logger.error(f"Transcription error: {result.error}")
        return ""

    return result.text.strip() if result.text else ""


async def get_speaker_info(audio_path: str) -> tuple[str, int]:
    """Run speaker diarization if available."""
    from app.services.audio.diarization import is_diarization_available, run_diarization

    if not is_diarization_available():
        logger.info("Speaker diarization not available (no HuggingFace token)")
        return "", 0

    logger.info("Running speaker diarization...")
    try:
        result = await run_diarization(audio_path)
        if result and result.segments:
            info = f"{result.num_speakers} speakers detected"
            return info, result.num_speakers
    except Exception as e:
        logger.warning(f"Diarization failed: {e}")

    return "", 0


# --- Output Rendering ---


def format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def render_markdown(
    summary: dict[str, Any],
    frames: list[dict],
    title: str,
    source: str,
    duration: float,
    output_path: Path,
    embed_images: bool = True,
) -> Path:
    """Generate markdown summary with embedded images."""
    md_parts = [f"# {title}\n"]

    # Metadata
    md_parts.append(f"**Source:** {source}")
    md_parts.append(f"**Duration:** {format_timestamp(duration)}")
    if summary.get("frames_analyzed"):
        md_parts.append(f"**Keyframes Analyzed:** {summary['frames_analyzed']}")
    md_parts.append("")

    # Main content from Gemini
    if summary.get("error"):
        md_parts.append(f"> Note: AI analysis failed ({summary['error']}). Showing transcript.\n")

    md_parts.append(summary.get("raw", ""))

    # Add keyframe gallery at the end if we have frames
    if frames and embed_images:
        md_parts.append("\n---\n")
        md_parts.append("## Keyframes\n")
        for frame in frames[:12]:  # Limit gallery size
            timestamp = format_timestamp(frame["timestamp"])
            frame_path = frame["path"]
            if Path(frame_path).exists():
                md_parts.append(f"### {timestamp}")
                md_parts.append(f"![Keyframe at {timestamp}]({frame_path})\n")

    content = "\n".join(md_parts)
    output_file = output_path.with_suffix(".md")
    output_file.write_text(content, encoding="utf-8")
    return output_file


def render_html(
    summary: dict[str, Any],
    frames: list[dict],
    title: str,
    source: str,
    duration: float,
    output_path: Path,
) -> Path:
    """Generate interactive HTML summary with embedded images."""
    import html as html_module

    # Inline CSS for self-contained HTML
    css = """
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
            color: #333;
            background: #fafafa;
        }
        h1 { color: #1a1a1a; border-bottom: 2px solid #007acc; padding-bottom: 0.5rem; }
        h2 { color: #007acc; margin-top: 2rem; }
        h3 { color: #555; }
        .meta { color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }
        .meta span { margin-right: 1.5rem; }
        .content { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .keyframes { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; margin-top: 1rem; }
        .keyframe { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .keyframe img { width: 100%; height: auto; display: block; }
        .keyframe-time { padding: 0.5rem; font-size: 0.85rem; color: #666; text-align: center; }
        pre { background: #f5f5f5; padding: 1rem; border-radius: 4px; overflow-x: auto; }
        code { font-family: 'SF Mono', Consolas, monospace; }
        ul, ol { padding-left: 1.5rem; }
        li { margin-bottom: 0.5rem; }
        blockquote { border-left: 3px solid #007acc; margin: 1rem 0; padding-left: 1rem; color: #555; }
    </style>
    """

    # Convert markdown-ish content to basic HTML
    content = summary.get("raw", "")
    # Basic markdown to HTML (headers, bold, lists)
    content = html_module.escape(content)
    content = content.replace("\n\n", "</p><p>")
    content = content.replace("\n- ", "</p><ul><li>")
    content = content.replace("\n", "<br>")
    content = f"<p>{content}</p>"

    # Build keyframes gallery
    keyframes_html = ""
    if frames:
        keyframes_html = '<div class="keyframes">'
        for frame in frames[:12]:
            timestamp = format_timestamp(frame["timestamp"])
            frame_path = frame["path"]
            if Path(frame_path).exists():
                # Embed as base64 for self-contained HTML
                try:
                    with open(frame_path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode()
                    keyframes_html += f"""
                    <div class="keyframe">
                        <img src="data:image/jpeg;base64,{img_data}" alt="Keyframe at {timestamp}">
                        <div class="keyframe-time">{timestamp}</div>
                    </div>
                    """
                except Exception:
                    pass
        keyframes_html += "</div>"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html_module.escape(title)}</title>
    {css}
</head>
<body>
    <h1>{html_module.escape(title)}</h1>
    <div class="meta">
        <span><strong>Source:</strong> {html_module.escape(source)}</span>
        <span><strong>Duration:</strong> {format_timestamp(duration)}</span>
    </div>
    <div class="content">
        {content}
    </div>
    <h2>Keyframes</h2>
    {keyframes_html}
</body>
</html>
"""

    output_file = output_path.with_suffix(".html")
    output_file.write_text(html_content, encoding="utf-8")
    return output_file


# --- Main Pipeline ---


async def process_video(
    input_path: str,
    verbosity: str = "chapter",
    output_format: str = "md",
    enable_speakers: bool = True,
    output_dir: Path | None = None,
    whisper_model: str = "small",
) -> Path | None:
    """Main video processing pipeline.

    Args:
        input_path: URL or local file path
        verbosity: 'minimal', 'chapter', or 'comprehensive'
        output_format: 'md', 'html', or 'both'
        enable_speakers: Whether to run speaker diarization
        output_dir: Output directory (defaults to current dir)
        whisper_model: Whisper model size

    Returns:
        Path to primary output file, or None on failure
    """
    if output_dir is None:
        output_dir = Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="summarize_") as temp_dir:
        # 1. Download if URL, otherwise use local file
        if is_url(input_path):
            platform = detect_platform(input_path)
            if not platform:
                logger.error("Unsupported URL. Supported: YouTube, TikTok, X/Twitter, Rumble")
                return None

            video_path, title, info = await download_video(input_path, temp_dir, platform)
            source = info.get("webpage_url", input_path)
            duration = info.get("duration", 0) or get_video_duration(video_path)
        else:
            if not os.path.exists(input_path):
                logger.error(f"File not found: {input_path}")
                return None

            video_path = input_path
            title = Path(input_path).stem
            source = str(Path(input_path).absolute())
            duration = get_video_duration(video_path)

        logger.info(f"Processing: {title} ({format_timestamp(duration)})")

        # 2. Extract audio and transcribe
        audio_path = extract_audio(video_path, temp_dir)
        transcript = await transcribe_video(audio_path, whisper_model)

        if not transcript:
            logger.error("Transcription failed")
            return None

        # 3. Speaker diarization (optional)
        speaker_info = ""
        num_speakers = 0
        if enable_speakers:
            speaker_info, num_speakers = await get_speaker_info(audio_path)

        # 4. Detect scenes and extract keyframes
        scenes = detect_scenes(video_path)
        frames = await extract_keyframes(video_path, scenes, temp_dir)

        # 5. Analyze with Gemini
        summary = await analyze_with_gemini(
            frames, transcript, verbosity, speaker_info, title
        )

        # 6. Render outputs
        safe_title = sanitize_filename(title)[:80]
        output_base = output_dir / safe_title
        primary_output = None

        if output_format in ("md", "both"):
            md_path = render_markdown(
                summary, frames, title, source, duration, output_base
            )
            logger.info(f"Saved: {md_path}")
            primary_output = md_path

        if output_format in ("html", "both"):
            html_path = render_html(
                summary, frames, title, source, duration, output_base
            )
            logger.info(f"Saved: {html_path}")
            if primary_output is None:
                primary_output = html_path

        return primary_output


async def main():
    parser = argparse.ArgumentParser(
        description="Summarize videos with AI-powered visual analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "https://youtu.be/VIDEO_ID"
  %(prog)s meeting.mp4 --verbosity comprehensive
  %(prog)s lecture.mp4 --verbosity minimal --no-speakers
  %(prog)s demo.mp4 --format html -o ~/summaries/
        """,
    )

    parser.add_argument("input", help="Video URL or file path")
    parser.add_argument(
        "--verbosity",
        "-v",
        choices=["minimal", "chapter", "comprehensive"],
        default="chapter",
        help="Summary detail level (default: chapter)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["md", "html", "both"],
        default="md",
        help="Output format (default: md)",
    )
    parser.add_argument(
        "--no-speakers",
        action="store_true",
        help="Disable speaker diarization",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path.cwd(),
        help="Output directory (default: current directory)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="small",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: small)",
    )

    args = parser.parse_args()

    # Validate Gemini API key early
    from app.config import settings

    if not settings.GEMINI_API_KEY.get_secret_value():
        logger.warning(
            "GEMINI_API_KEY not set. Add it to .env for AI-powered summaries. "
            "Continuing with transcript-only mode."
        )

    result = await process_video(
        args.input,
        verbosity=args.verbosity,
        output_format=args.format,
        enable_speakers=not args.no_speakers,
        output_dir=args.output_dir,
        whisper_model=args.model,
    )

    if result:
        logger.info("Done!")
    else:
        logger.error("Processing failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
