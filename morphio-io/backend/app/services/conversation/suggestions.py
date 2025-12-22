"""Follow-up suggestion generation for conversations."""

from __future__ import annotations

from typing import Iterable, List, Optional


def generate_follow_up_suggestions(
    updated_content: str,
    change_summary: Iterable[str] | None = None,
    previous_request: Optional[str] = None,
) -> List[str]:
    """Generate contextual follow-up suggestions based on content changes.

    Args:
        updated_content: The current content state
        change_summary: List of changes made in the last update
        previous_request: The user's previous request (to avoid repeating)

    Returns:
        Up to 8 sorted suggestions for next actions
    """
    base_suggestions = {
        "Make it shorter",
        "Add more detail about the introduction",
        "Change tone to more formal",
        "Generate social media version",
        "Create bullet point summary",
        "Focus more on the technical aspects",
        "Remove the marketing language",
        "Convert this to a Twitter thread",
        "Create a LinkedIn post version",
        "What are the key takeaways?",
        "Generate FAQ from this content",
        "Suggest images for each section",
        "Generate SEO metadata",
    }

    suggestions = set(base_suggestions)

    content_length = len(updated_content)
    if content_length > 1500:
        suggestions.add("Make it shorter")
    elif content_length < 600:
        suggestions.add("Add more detail about key points")

    if change_summary:
        joined = " ".join(change_summary).lower()
        if "tone" not in joined:
            suggestions.add("Change tone to more conversational")

    if previous_request:
        normalized = previous_request.lower()
        to_remove = {s for s in suggestions if s.lower() in normalized}
        suggestions.difference_update(to_remove)

    return sorted(suggestions)[:8]
