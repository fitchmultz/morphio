"""Response parsing utilities for conversation content."""

from __future__ import annotations

import json
import logging
from typing import List, Optional, Tuple

from ..generation.core import sanitize_markdown

logger = logging.getLogger(__name__)


def strip_code_fences(raw: str) -> str:
    """Remove surrounding code fences from LLM response."""
    text = raw.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        while lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def parse_model_response(
    raw: str, original_content: str = ""
) -> Tuple[str, List[str], Optional[str]]:
    """Parse structured JSON response from LLM.

    Args:
        raw: Raw response string from the LLM
        original_content: Original content to fall back to if parsing fails

    Returns:
        Tuple of (updated_content, change_summary, notes)
    """
    payload = strip_code_fences(raw)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON; returning raw content")
        cleaned = sanitize_markdown(raw.strip())
        # If cleaned content is empty, preserve original content
        if not cleaned and original_content:
            logger.warning("Raw content is empty after sanitization; preserving original content")
            return original_content, [], None
        # If still empty, return a fallback message
        if not cleaned:
            logger.error("Both raw and original content are empty; returning error message")
            return "I apologize, but I couldn't generate a response. Please try again.", [], None
        return cleaned, [], None

    updated_content = sanitize_markdown(str(data.get("updated_content", "")).strip())
    summary = data.get("change_summary") or []
    notes = data.get("notes")

    if not isinstance(summary, list):  # type: ignore[unreachable]
        summary = [str(summary)]
    summary = [str(item).strip() for item in summary if str(item).strip()]

    # If updated_content is empty, fallback to original content or raw
    if not updated_content:
        if original_content:
            logger.warning("Updated content is empty from JSON; preserving original content")
            return original_content, summary, str(notes).strip() if notes else None
        fallback = raw.strip()
        if not fallback:
            logger.error("All content sources are empty; returning error message")
            return (
                "I apologize, but I couldn't generate a response. Please try again.",
                summary,
                str(notes).strip() if notes else None,
            )
        return fallback, summary, str(notes).strip() if notes else None

    return updated_content, summary, str(notes).strip() if notes else None


def render_assistant_message(
    updated_content: str, change_summary: List[str], notes: Optional[str]
) -> str:
    """Format assistant message for display.

    Args:
        updated_content: The updated content to display
        change_summary: List of changes made
        notes: Optional notes about the changes

    Returns:
        Formatted message string
    """
    parts: List[str] = []
    if change_summary:
        summary_block = "\n".join(f"- {item}" for item in change_summary)
        parts.append(f"### Change Summary\n{summary_block}")
    parts.append(updated_content)
    if notes:
        parts.append(f"> Note: {notes}")
    return "\n\n".join(parts).strip()
