#!/usr/bin/env python3
"""
Interactive URL Analyzer (standalone)

Features
- Prompts for a URL, then optional template selection from `backend/templates/*.json`.
- If no template selected: prints raw transcript/text.
- If a template is selected: calls OpenAI Responses API (configurable model + reasoning).

Requirements
- Python 3.13+ (tested for 3.11+ syntax compatibility).
- Env var: OPENAI_API_KEY.
- Optional deps: youtube-transcript-api, yt-dlp, httpx (already used in this repo).

Run
  $ python scripts/interactive_url_analyzer.py

Notes
- Does NOT import any project modules; only reads JSON templates from disk.
- Reasoning effort defaults to "medium" and model defaults to "gpt-5.1" (override interactively).
"""

from __future__ import annotations

import json
import os
import re
import sys
import textwrap
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, Optional


# --- Light HTML → text extraction (no external parser) -----------------------
class _BodyTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_script = False
        self._in_style = False
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs):  # type: ignore[override]
        if tag.lower() == "script":
            self._in_script = True
        elif tag.lower() == "style":
            self._in_style = True

    def handle_endtag(self, tag: str):  # type: ignore[override]
        if tag.lower() == "script":
            self._in_script = False
        elif tag.lower() == "style":
            self._in_style = False

    def handle_data(self, data: str):  # type: ignore[override]
        if not (self._in_script or self._in_style):
            d = data.strip()
            if d:
                self._chunks.append(d)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._chunks)).strip()


# --- Utilities ---------------------------------------------------------------
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}


def _is_youtube(url: str) -> bool:
    try:
        from urllib.parse import urlparse

        host = urlparse(url).netloc.lower()
        return any(h in host for h in YOUTUBE_HOSTS)
    except Exception:
        return False


def _extract_youtube_id(url: str) -> Optional[str]:
    from urllib.parse import urlparse, parse_qs

    p = urlparse(url)
    if p.netloc in {"youtu.be"}:
        vid = p.path.lstrip("/")
        return vid or None
    qs = parse_qs(p.query)
    if "v" in qs:
        return qs["v"][0]
    # Shorts or embed
    m = re.search(r"/(shorts|embed)/([\w-]{6,})", p.path)
    if m:
        return m.group(2)
    return None


def _join_transcript_chunks(chunks: Iterable[dict]) -> str:
    return " ".join((c.get("text", "").strip() for c in chunks if c.get("text"))).strip()


def _vtt_to_text(vtt: str) -> str:
    lines: list[str] = []
    for line in vtt.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("WEBVTT") or "-->" in s:
            continue
        if s.isdigit():
            continue
        lines.append(s)
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def fetch_transcript_or_text(url: str) -> str:
    """Return transcript for YouTube, else best-effort page text for generic URLs."""
    if _is_youtube(url):
        video_id = _extract_youtube_id(url)
        if video_id:
            # 1) Try youtube-transcript-api
            try:
                from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore

                transcript = YouTubeTranscriptApi.get_transcript(
                    video_id, languages=["en", "en-US", "en-GB"]
                )
                txt = _join_transcript_chunks(transcript)
                if txt:
                    return txt
            except Exception:
                pass

        # 2) Fallback to yt-dlp automatic captions (no download)
        try:
            import httpx  # type: ignore
            import yt_dlp  # type: ignore

            ydl_opts = {"skip_download": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            subs = info.get("subtitles") or info.get("automatic_captions") or {}
            track = (
                subs.get("en")
                or next((v for k, v in subs.items() if k.startswith("en")), None)
            )
            if track and isinstance(track, list) and track[0].get("url"):
                vtt = httpx.get(track[0]["url"], timeout=30).text
                txt = _vtt_to_text(vtt)
                if txt:
                    return txt
        except Exception:
            pass

        raise RuntimeError("No transcript available for this YouTube URL.")

    # Generic webpage: fetch and extract text
    try:
        import httpx  # type: ignore

        with httpx.Client(follow_redirects=True, timeout=30) as client:
            r = client.get(url)
            r.raise_for_status()
            html = r.text
    except Exception as e:
        raise RuntimeError(f"Failed to fetch URL: {e}")

    parser = _BodyTextExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    text = parser.text()
    if not text or len(text) < 30:
        raise RuntimeError("Extracted text is empty or too short.")
    return text


# --- Templates ---------------------------------------------------------------
@dataclass
class TemplateInfo:
    name: str
    path: Path
    content: str  # template_content


def discover_templates(templates_dir: Path) -> list[TemplateInfo]:
    results: list[TemplateInfo] = []
    for p in sorted(templates_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            name = data.get("name") or p.stem
            content = data.get("template_content") or ""
            if content:
                results.append(TemplateInfo(name=name, path=p, content=content))
        except Exception:
            continue
    return results


# --- OpenAI Responses --------------------------------------------------------
def call_openai_responses(
    *,
    transcript: str,
    template_text: str,
    model: str,
    reasoning_effort: str,
) -> str:
    """Call OpenAI Responses API; returns plain text content."""
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError(
            f"openai package is required to use templates: {e}"
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in the environment.")

    client = OpenAI()
    system_text = (
        "You are an expert content creator. Respond in valid, concise Markdown."
    )
    user_text = textwrap.dedent(
        f"""
        Instructions:\n{template_text}

        Transcript/Text:\n{transcript}
        """
    ).strip()

    try:
        # Responses API
        resp = client.responses.create(
            model=model,
            reasoning={"effort": reasoning_effort},
            input=[
                {
                    "role": "system",
                    "content": [
                        {"type": "text", "text": system_text},
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                    ],
                },
            ],
        )
    except Exception as e:
        # Fallback: try Chat Completions if Responses unsupported
        try:
            chat = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": user_text},
                ],
            )
            return chat.choices[0].message.content or ""
        except Exception as e2:
            raise RuntimeError(f"OpenAI call failed: {e2 or e}")

    # Newer SDKs expose resp.output_text
    output_text = getattr(resp, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    # Generic extraction path
    try:
        for item in resp.output:  # type: ignore[attr-defined]
            if getattr(item, "type", None) == "message":
                parts = getattr(item, "content", [])
                for p in parts:
                    if getattr(p, "type", None) == "text":
                        val = getattr(p, "text", "")
                        if val:
                            return val
    except Exception:
        pass
    return ""


# --- Interactive flow --------------------------------------------------------
def prompt_input(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(1)


def main() -> None:
    print("Interactive URL Analyzer — lightweight, standalone")

    url = prompt_input("Enter URL: ").strip()
    if not url:
        print("No URL provided.")
        sys.exit(1)

    # Locate templates directory (default to backend/templates)
    default_templates_dir = Path("backend") / "templates"
    templates_dir_input = prompt_input(
        f"Templates directory [{default_templates_dir}]: "
    ).strip()
    templates_dir = (
        Path(templates_dir_input) if templates_dir_input else default_templates_dir
    )

    templates: list[TemplateInfo] = []
    if templates_dir.exists():
        templates = discover_templates(templates_dir)

    # Present selection
    print("\nTemplates:")
    if templates:
        for i, t in enumerate(templates, start=1):
            print(f"  {i}. {t.name} ({t.path.name})")
    else:
        print("  (none discovered — press Enter to skip)")

    sel = prompt_input(
        "Select template number (or Enter for raw transcript): "
    ).strip()

    try:
        selected: Optional[TemplateInfo]
        if sel:
            idx = int(sel)
            selected = templates[idx - 1]
        else:
            selected = None
    except Exception:
        print("Invalid selection.")
        sys.exit(1)

    print("\nFetching transcript/text...")
    try:
        transcript = fetch_transcript_or_text(url)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not selected:
        print("\n--- Raw Transcript/Text ---\n")
        print(transcript)
        return

    # With template → OpenAI Responses
    model = prompt_input("Model [gpt-5.1]: ").strip() or "gpt-5.1"
    effort = (
        prompt_input("Reasoning effort [medium] (low|medium|high): ").strip() or "medium"
    )
    if effort not in {"low", "medium", "high"}:
        print("Invalid effort; using 'medium'.")
        effort = "medium"

    print("\nCalling OpenAI... (this may take a moment)")
    try:
        out = call_openai_responses(
            transcript=transcript,
            template_text=selected.content,
            model=model,
            reasoning_effort=effort,
        )
    except Exception as e:
        print(f"OpenAI error: {e}")
        sys.exit(1)

    print("\n--- Generated Output ---\n")
    print(out or "<no content returned>")


if __name__ == "__main__":
    main()


# hook test
