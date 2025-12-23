"""
Content generation service using morphio-core LLM router.

This module provides content generation functions that use the centralized
LLM adapter for all provider interactions.
"""

import logging

from morphio_core.llm import sanitize_markdown

from ...adapters.llm import (
    MODEL_DISPLAY_INFO,
    MODEL_TOKEN_LIMITS,
    VALID_GENERATION_MODELS,
    generate_completion,
    get_model_token_limit,
)
from ...config import settings

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = [
    "MODEL_TOKEN_LIMITS",
    "MODEL_DISPLAY_INFO",
    "VALID_GENERATION_MODELS",
    "sanitize_markdown",
    "generate_content_title",
    "generate_content_from_transcript",
    "generate_conversation_completion",
]


async def generate_content_title(content: str) -> str:
    """Generate a concise title for the content."""
    prompt_context = (
        "Read and understand the provided context.\n"
        "Task: Generate a single, concise title that accurately reflects the content's essence.\n"
        "Constraints:\n"
        "- Do NOT use quotation marks or other punctuation in the final title.\n"
        "- Aim for brevity and clarity.\n"
        "Output Format: Provide ONLY the final title as plain text. NO other commentary.\n"
    )

    user_excerpt = content[:500].strip()
    messages = [
        {"role": "system", "content": prompt_context},
        {"role": "user", "content": f"Here is the content excerpt:\n{user_excerpt}"},
    ]

    generated_title, _ = await generate_completion(
        messages=messages,
        model=settings.TITLE_GENERATION_MODEL,
        max_tokens=35,
    )

    return generated_title.strip().strip('"')


async def generate_content_from_transcript(
    transcript: str, template_content: str, chosen_model: str = ""
) -> str:
    """Generate content from a transcript and template using an LLM."""
    logger.debug(
        f"Called generate_content_from_transcript with chosen_model: {chosen_model} "
        f"(type: {type(chosen_model)})"
    )

    # Validate model choice
    if not chosen_model or chosen_model not in VALID_GENERATION_MODELS:
        used_model = settings.CONTENT_MODEL
        logger.debug(f"Using default model: {used_model}")
    else:
        used_model = chosen_model
        logger.debug(f"Using provided model: {used_model}")

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert content creator. "
                "Respond in valid markdown format. Follow the instructions precisely."
            ),
        },
        {
            "role": "user",
            "content": f"Instructions:\n{template_content}\n\nTranscript:\n{transcript}",
        },
    ]

    generated, _ = await generate_completion(
        messages=messages,
        model=used_model,
        max_tokens=get_model_token_limit(used_model),
    )

    return sanitize_markdown(generated)


async def generate_conversation_completion(
    messages: list[dict[str, str]],
    chosen_model: str | None = None,
    max_completion_tokens: int | None = None,
) -> tuple[str, str]:
    """Run a conversational completion with the configured provider.

    Returns a tuple of (markdown_content, model_used).
    """
    # Determine model to use
    if not chosen_model:
        used_model = settings.CONTENT_MODEL
    else:
        used_model = chosen_model

    # Calculate token budget
    model_token_limit = get_model_token_limit(used_model)
    budget = min(max_completion_tokens if max_completion_tokens is not None else 2048, model_token_limit)

    generated, model_used = await generate_completion(
        messages=messages,
        model=used_model,
        max_tokens=budget,
    )

    return sanitize_markdown(generated), model_used
