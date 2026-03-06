"""
Content generation service using morphio-core LLM router.

This module provides content generation functions that use the centralized
LLM adapter for all provider interactions.
"""

import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ...adapters.llm import (
    MODEL_DISPLAY_INFO,
    MODEL_TOKEN_LIMITS,
    VALID_GENERATION_MODELS,
    generate_completion,
    generate_completion_with_usage,
    get_model_token_limit,
    resolve_model_alias,
    sanitize_markdown,
)
from ...config import settings
from ...utils.enums import UsageType
from ..usage import check_usage_limit, record_llm_usage

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = [
    "MODEL_TOKEN_LIMITS",
    "MODEL_DISPLAY_INFO",
    "VALID_GENERATION_MODELS",
    "sanitize_markdown",
    "generate_content_title",
    "generate_content_from_transcript",
    "generate_content_from_transcript_tracked",
    "generate_conversation_completion",
    "generate_conversation_completion_tracked",
]


def resolve_generation_model(chosen_model: str | None = None) -> str:
    """Resolve a configured model alias to a currently supported stable model."""
    if chosen_model and chosen_model in VALID_GENERATION_MODELS:
        return chosen_model

    configured_default = settings.CONTENT_MODEL
    if configured_default in VALID_GENERATION_MODELS:
        return configured_default

    fallback_model = "gemini-3-flash-preview-minimal"
    logger.warning(
        "CONTENT_MODEL '%s' is invalid; falling back to '%s'",
        configured_default,
        fallback_model,
    )
    return fallback_model


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

    title_model = settings.TITLE_GENERATION_MODEL
    if title_model not in VALID_GENERATION_MODELS:
        fallback_model = resolve_generation_model()
        logger.warning(
            "TITLE_GENERATION_MODEL '%s' is invalid; falling back to '%s'",
            title_model,
            fallback_model,
        )
        title_model = fallback_model

    generated_title, _ = await generate_completion(
        messages=messages,
        model=title_model,
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

    used_model = resolve_generation_model(chosen_model)
    logger.debug(f"Using resolved model: {used_model}")

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


async def generate_content_from_transcript_tracked(
    transcript: str,
    template_content: str,
    chosen_model: str,
    *,
    db: AsyncSession,
    user_id: int,
    content_id: int | None = None,
) -> str:
    """Generate content from a transcript with token usage tracking and limit enforcement.

    This version:
    - Checks usage limits BEFORE generation (fails fast with 403)
    - Records LLM token usage for usage analytics and auditability

    Args:
        transcript: The audio transcript to process
        template_content: Template instructions for content generation
        chosen_model: Model alias to use (e.g., "gpt-5.2-high")
        db: Database session for recording usage
        user_id: User who triggered the generation
        content_id: Optional content ID for attribution

    Returns:
        Generated markdown content

    Raises:
        ApplicationException: 403 if user has exceeded their usage limit
    """
    # Check usage limit BEFORE expensive LLM call
    await check_usage_limit(db, user_id, UsageType.CONTENT_GENERATION)

    logger.debug(f"Generating content with tracking: model={chosen_model}, user={user_id}")

    used_model = resolve_generation_model(chosen_model)

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

    result = await generate_completion_with_usage(
        messages=messages,
        model=used_model,
        max_tokens=get_model_token_limit(used_model),
    )

    # Record token usage
    _, provider, _ = resolve_model_alias(used_model)
    await record_llm_usage(
        db,
        user_id=user_id,
        provider=provider,
        model=result.model or used_model,
        input_tokens=result.input_tokens or 0,
        output_tokens=result.output_tokens or 0,
        model_alias=used_model,
        content_id=content_id,
        operation="content_generation",
        cost_usd=Decimal(str(result.cost_usd)) if result.cost_usd else None,
    )

    logger.debug(
        f"Recorded LLM usage: in={result.input_tokens or 0}, out={result.output_tokens or 0}, "
        f"model={result.model or used_model}"
    )

    return sanitize_markdown(result.content)


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
        used_model = resolve_generation_model()
    else:
        used_model = resolve_generation_model(chosen_model)

    # Calculate token budget
    model_token_limit = get_model_token_limit(used_model)
    budget = min(
        max_completion_tokens if max_completion_tokens is not None else 2048, model_token_limit
    )

    generated, model_used = await generate_completion(
        messages=messages,
        model=used_model,
        max_tokens=budget,
    )

    return sanitize_markdown(generated), model_used


async def generate_conversation_completion_tracked(
    messages: list[dict[str, str]],
    *,
    db: AsyncSession,
    user_id: int,
    content_id: int | None = None,
    chosen_model: str | None = None,
    max_completion_tokens: int | None = None,
) -> tuple[str, str]:
    """Run a conversational completion with token usage tracking and limit enforcement.

    This version:
    - Checks usage limits BEFORE generation (fails fast with 403)
    - Records LLM token usage for usage analytics and auditability

    Args:
        messages: Conversation history
        db: Database session for recording usage
        user_id: User who triggered the generation
        content_id: Optional content ID for attribution
        chosen_model: Model alias to use
        max_completion_tokens: Max tokens in response

    Returns:
        Tuple of (markdown_content, model_used)

    Raises:
        ApplicationException: 403 if user has exceeded their usage limit
    """
    # Check usage limit BEFORE expensive LLM call
    await check_usage_limit(db, user_id, UsageType.CONTENT_GENERATION)

    # Determine model to use
    if not chosen_model:
        used_model = settings.CONTENT_MODEL
    else:
        used_model = chosen_model

    # Calculate token budget
    model_token_limit = get_model_token_limit(used_model)
    budget = min(
        max_completion_tokens if max_completion_tokens is not None else 2048, model_token_limit
    )

    result = await generate_completion_with_usage(
        messages=messages,
        model=used_model,
        max_tokens=budget,
    )

    # Record token usage
    _, provider, _ = resolve_model_alias(used_model)
    await record_llm_usage(
        db,
        user_id=user_id,
        provider=provider,
        model=result.model or used_model,
        input_tokens=result.input_tokens or 0,
        output_tokens=result.output_tokens or 0,
        model_alias=used_model,
        content_id=content_id,
        operation="conversation",
        cost_usd=Decimal(str(result.cost_usd)) if result.cost_usd else None,
    )

    logger.debug(
        f"Recorded conversation LLM usage: in={result.input_tokens or 0}, out={result.output_tokens or 0}"
    )

    return sanitize_markdown(result.content), result.model or used_model
