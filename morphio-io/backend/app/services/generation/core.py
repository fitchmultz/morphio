import logging
import re

import anthropic
from google.genai import types

from ...config import settings
from ...utils.error_handlers import ApplicationException, handle_openai_exception

logger = logging.getLogger(__name__)

MODEL_TOKEN_LIMITS = {
    # OpenAI models
    "gpt-5.1": 128000,  # Max output tokens for gpt-5.1 (context window: 400,000)
    "gpt-5.1-nano": 128000,  # Max output tokens for gpt-5.1 Nano (context window: 400,000)
    "gpt-5.1-low": 128000,  # Max output tokens for gpt-5.1 (context window: 400,000)
    "gpt-5.1-medium": 128000,  # Max output tokens for gpt-5.1 (context window: 400,000)
    "gpt-5.1-high": 128000,  # Max output tokens for gpt-5.1 (context window: 400,000)
    # Anthropic models
    "claude-4-sonnet": 16384,
    # Gemini 3 Flash variants (65536 max output tokens)
    "gemini-3-flash-preview": 65536,
    "gemini-3-flash-preview-medium": 65536,
    "gemini-3-flash-preview-low": 65536,
    "gemini-3-flash-preview-minimal": 65536,
    # Gemini 3 Pro variants (65536 max output tokens)
    "gemini-3-pro-preview": 65536,
    "gemini-3-pro-preview-low": 65536,
}

ANTHROPIC_STOP = anthropic.HUMAN_PROMPT

# Valid models for content generation (derived from MODEL_TOKEN_LIMITS)
VALID_GENERATION_MODELS = list(MODEL_TOKEN_LIMITS.keys())

# Display labels for UI (order matters - first is default)
MODEL_DISPLAY_INFO = [
    # Gemini 3 Flash (default group - supports HIGH, MEDIUM, LOW, MINIMAL)
    {"id": "gemini-3-flash-preview", "label": "Gemini 3 Flash (High)"},
    {"id": "gemini-3-flash-preview-medium", "label": "Gemini 3 Flash (Medium)"},
    {"id": "gemini-3-flash-preview-low", "label": "Gemini 3 Flash (Low)"},
    {"id": "gemini-3-flash-preview-minimal", "label": "Gemini 3 Flash (Minimal)"},
    # Gemini 3 Pro (supports HIGH, LOW only)
    {"id": "gemini-3-pro-preview", "label": "Gemini 3 Pro (High)"},
    {"id": "gemini-3-pro-preview-low", "label": "Gemini 3 Pro (Low)"},
    # Legacy models
    {"id": "gpt-5.1", "label": "GPT-5.1"},
    {"id": "gpt-5.1-high", "label": "GPT-5.1 (High Reasoning)"},
    {"id": "gpt-5.1-medium", "label": "GPT-5.1 (Medium Reasoning)"},
    {"id": "gpt-5.1-low", "label": "GPT-5.1 (Low Reasoning)"},
    {"id": "claude-4-sonnet", "label": "Claude 4 Sonnet"},
]


def _normalize_model_choice(chosen_model: str | None) -> str:
    if not chosen_model:
        return settings.CONTENT_MODEL
    return chosen_model


def _resolve_openai_model(chosen_model: str) -> tuple[str, dict[str, str]]:
    """Return the base model name and optional reasoning parameters for OpenAI requests."""
    base_model = chosen_model
    params: dict[str, str] = {}
    if chosen_model.startswith("gpt-5.1"):
        base_model = "gpt-5.1"
        if chosen_model == "gpt-5.1-low":
            params["reasoning_effort"] = "low"
        elif chosen_model == "gpt-5.1-medium":
            params["reasoning_effort"] = "medium"
        elif chosen_model == "gpt-5.1-high":
            params["reasoning_effort"] = "high"
    return base_model, params


def _resolve_gemini_model(chosen_model: str) -> tuple[str, types.ThinkingLevel]:
    """Return the base model name and thinking level for Gemini requests."""
    PRO_THINKING_LEVELS = {types.ThinkingLevel.HIGH, types.ThinkingLevel.LOW}

    # Parse model and extract thinking level
    if chosen_model.endswith("-minimal"):
        base_model = chosen_model.removesuffix("-minimal")
        thinking_level = types.ThinkingLevel.MINIMAL
    elif chosen_model.endswith("-medium"):
        base_model = chosen_model.removesuffix("-medium")
        thinking_level = types.ThinkingLevel.MEDIUM
    elif chosen_model.endswith("-low"):
        base_model = chosen_model.removesuffix("-low")
        thinking_level = types.ThinkingLevel.LOW
    else:
        base_model = chosen_model
        thinking_level = types.ThinkingLevel.HIGH

    # Validate thinking level for Pro models
    if "pro" in base_model and thinking_level not in PRO_THINKING_LEVELS:
        logger.warning(f"Gemini Pro doesn't support {thinking_level}, defaulting to HIGH")
        thinking_level = types.ThinkingLevel.HIGH

    return (base_model, thinking_level)


def _get_gemini_setup(chosen_model: str, context: str = "generation"):
    """Validate API key and return Gemini client with resolved model info.

    Args:
        chosen_model: The Gemini model ID (e.g. "gemini-3-flash-preview-medium")
        context: Description for error logging (e.g. "title generation", "content generation")

    Returns:
        Tuple of (gemini_client, base_model, thinking_level)

    Raises:
        ApplicationException: If Gemini API key is missing
    """
    if not settings.GEMINI_API_KEY.get_secret_value():
        logger.error(f"Gemini API key missing but Gemini model requested for {context}")
        raise ApplicationException("Gemini API key missing for Gemini model", 500)

    gemini_client = settings.gemini_client
    base_model, thinking_level = _resolve_gemini_model(chosen_model)
    logger.debug(f"Using Gemini model: {base_model} with thinking level: {thinking_level}")

    return gemini_client, base_model, thinking_level


def _build_gemini_contents(
    messages: list[dict[str, str]],
) -> tuple[list[types.Content], str | None]:
    """Convert messages to Gemini format. Returns (contents, system_instruction)."""
    contents: list[types.Content] = []
    system_parts: list[str] = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role in {"system", "developer"}:
            system_parts.append(content)  # Collect for system_instruction
        elif role == "assistant":
            contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))
        else:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))

    system_instruction = "\n\n".join(system_parts) if system_parts else None
    return (contents, system_instruction)


def sanitize_markdown(content: str) -> str:
    """Ensure code blocks are properly closed and remove stray backticks."""
    # Find all code blocks
    pattern = r"```[\s\S]*?(```|$)"
    matches = re.finditer(pattern, content)

    sanitized = content
    for match in matches:
        block = match.group(0)
        if not block.endswith("```"):
            sanitized = sanitized.replace(block, block + "```")

    # Escape stray backticks not part of a code block
    sanitized = re.sub(r"(?<!`)`(?!`)", r"\`", sanitized)
    return sanitized


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
    # Ensure we're using a valid model
    used_model = settings.TITLE_GENERATION_MODEL
    user_excerpt = content[:500].strip()

    if used_model.startswith("claude"):
        if not settings.ANTHROPIC_API_KEY.get_secret_value():
            logger.error(
                "Anthropic API key missing but Claude model requested for title generation"
            )
            raise ApplicationException("Anthropic API key missing for Claude model", 500)

        prompt_text = (
            f"{anthropic.HUMAN_PROMPT}System:\n{prompt_context}\n\n"
            f"{anthropic.HUMAN_PROMPT}User:\n{user_excerpt}\n"
            f"{anthropic.AI_PROMPT}"
        )
        try:
            anthropic_client = settings.anthropic_client
            resp = await anthropic_client.completions.create(
                model=used_model,
                prompt=prompt_text,
                max_tokens_to_sample=35,
                temperature=settings.CONTENT_TEMPERATURE,
                stop_sequences=[ANTHROPIC_STOP],
            )
            generated_title = resp.completion.strip()
            return generated_title.strip('"')
        except Exception as e:
            logger.error(f"Error generating content title (Anthropic): {e}", exc_info=True)
            raise handle_openai_exception(e)

    elif used_model.startswith("gemini"):
        gemini_client, base_model, thinking_level = _get_gemini_setup(
            used_model, "title generation"
        )

        try:
            response = await gemini_client.aio.models.generate_content(
                model=base_model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=user_excerpt)],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=prompt_context,
                    temperature=settings.CONTENT_TEMPERATURE,
                    max_output_tokens=35,
                    thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
                    media_resolution=settings.GEMINI_MEDIA_RESOLUTION,
                ),
            )
            generated_title = (response.text or "").strip()
            return generated_title.strip('"')
        except Exception as e:
            logger.error(f"Error generating content title (Gemini): {e}", exc_info=True)
            raise handle_openai_exception(e)

    else:
        try:
            openai_client = settings.openai_client

            # Prepare the API call parameters
            api_params = {
                "messages": [
                    {
                        "role": "developer",
                        "content": f"{prompt_context}",
                    },
                    {
                        "role": "user",
                        "content": f"Here is the content excerpt:\n{user_excerpt}",
                    },
                ],
                "max_completion_tokens": 35,
                "temperature": settings.CONTENT_TEMPERATURE,
            }

            base_model, extra_params = _resolve_openai_model(used_model)
            api_params["model"] = base_model
            api_params.update(extra_params)

            completion = await openai_client.chat.completions.create(**api_params)
            raw = completion.choices[0].message.content
            generated_title = (raw or "").strip()
            return generated_title.strip('"')
        except Exception as e:
            logger.error(f"Error generating content title (OpenAI): {e}", exc_info=True)
            raise handle_openai_exception(e)


async def generate_content_from_transcript(
    transcript: str, template_content: str, chosen_model: str = ""
) -> str:
    """Generate content from a transcript and template using an LLM."""
    logger.debug(
        f"Called generate_content_from_transcript with chosen_model: {chosen_model} "
        f"(type: {type(chosen_model)})"
    )

    # Check if chosen_model is a valid model name
    if not chosen_model or chosen_model not in VALID_GENERATION_MODELS:
        used_model = settings.CONTENT_MODEL
        logger.debug(f"Using default model: {used_model}")
    else:
        used_model = chosen_model
        logger.debug(f"Using provided model: {used_model}")

    model_token_limit = MODEL_TOKEN_LIMITS.get(used_model, 8192)

    if used_model.startswith("claude"):
        if not settings.ANTHROPIC_API_KEY.get_secret_value():
            logger.error(
                "Anthropic API key missing but Claude model requested for content generation"
            )
            raise ApplicationException("Anthropic API key missing for Claude model", 500)

        instructions = template_content
        prompt_text = (
            f"{anthropic.HUMAN_PROMPT}System:\n"
            "You are an expert content creator. Respond in valid markdown format.\n"
            "Follow the user's instructions precisely.\n\n"
            f"{anthropic.HUMAN_PROMPT}User Instructions:\n{instructions}\n\n"
            f"Transcript:\n{transcript}\n"
            f"{anthropic.AI_PROMPT}"
        )
        try:
            anthropic_client = settings.anthropic_client
            resp = await anthropic_client.completions.create(
                model=used_model,
                prompt=prompt_text,
                max_tokens_to_sample=model_token_limit,
                temperature=settings.CONTENT_TEMPERATURE,
                stop_sequences=[ANTHROPIC_STOP],
            )
            generated = resp.completion
            return sanitize_markdown(generated)
        except Exception as e:
            logger.error(f"Error generating content (Anthropic): {e}", exc_info=True)
            raise handle_openai_exception(e)

    elif used_model.startswith("gemini"):
        gemini_client, base_model, thinking_level = _get_gemini_setup(
            used_model, "content generation"
        )
        instructions = template_content

        try:
            system_instruction = (
                "You are an expert content creator. "
                "Respond in valid markdown format. Follow the instructions precisely."
            )
            user_content = f"Instructions:\n{instructions}\n\nTranscript:\n{transcript}"

            response = await gemini_client.aio.models.generate_content(
                model=base_model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=user_content)],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=settings.CONTENT_TEMPERATURE,
                    max_output_tokens=model_token_limit,
                    thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
                    media_resolution=settings.GEMINI_MEDIA_RESOLUTION,
                ),
            )
            generated = response.text or ""
            return sanitize_markdown(generated)
        except Exception as e:
            logger.error(f"Error generating content (Gemini): {e}", exc_info=True)
            raise handle_openai_exception(e)

    else:
        instructions = template_content
        try:
            openai_client = settings.openai_client

            api_params = {
                "messages": [
                    {
                        "role": "developer",
                        "content": "Formatting re-enabled. You are an expert content creator. "
                        "Respond in valid markdown format. Follow the instructions precisely.",
                    },
                    {
                        "role": "user",
                        "content": f"Instructions:\n{instructions}\n\nTranscript:\n{transcript}",
                    },
                ],
                "max_completion_tokens": model_token_limit,
                "temperature": settings.CONTENT_TEMPERATURE,
            }

            base_model, extra_params = _resolve_openai_model(used_model)
            api_params["model"] = base_model
            api_params.update(extra_params)

            completion = await openai_client.chat.completions.create(**api_params)
            raw = completion.choices[0].message.content or ""
            return sanitize_markdown(raw)
        except Exception as e:
            logger.error(f"Error generating content (OpenAI): {e}", exc_info=True)
            raise handle_openai_exception(e)


def _build_anthropic_prompt_from_messages(messages: list[dict[str, str]]) -> str:
    prompt_parts: list[str] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role in {"system", "developer"}:
            prompt_parts.append(f"{anthropic.HUMAN_PROMPT}System:\n{content}\n")
        elif role == "assistant":
            prompt_parts.append(f"{anthropic.AI_PROMPT}{content}\n")
        else:
            prompt_parts.append(f"{anthropic.HUMAN_PROMPT}User:\n{content}\n")
    prompt_parts.append(anthropic.AI_PROMPT)
    return "".join(prompt_parts)


async def generate_conversation_completion(
    messages: list[dict[str, str]],
    chosen_model: str | None = None,
    max_completion_tokens: int | None = None,
) -> tuple[str, str]:
    """Run a conversational completion with the configured provider.

    Returns a tuple of (markdown_content, model_used).
    """
    used_model = _normalize_model_choice(chosen_model)
    model_token_limit = MODEL_TOKEN_LIMITS.get(used_model, 8192)
    budget = min(max_completion_tokens or 2048, model_token_limit)

    if used_model.startswith("claude"):
        if not settings.ANTHROPIC_API_KEY.get_secret_value():
            logger.error(
                "Anthropic API key missing but Claude model requested for conversation generation"
            )
            raise ApplicationException("Anthropic API key missing for Claude model", 500)

        prompt_text = _build_anthropic_prompt_from_messages(messages)
        try:
            anthropic_client = settings.anthropic_client
            resp = await anthropic_client.completions.create(
                model=used_model,
                prompt=prompt_text,
                max_tokens_to_sample=budget,
                temperature=settings.CONTENT_TEMPERATURE,
                stop_sequences=[ANTHROPIC_STOP],
            )
            generated = resp.completion or ""
            return sanitize_markdown(generated), used_model
        except Exception as e:
            logger.error(f"Error generating conversation content (Anthropic): {e}", exc_info=True)
            raise handle_openai_exception(e)

    elif used_model.startswith("gemini"):
        gemini_client, base_model, thinking_level = _get_gemini_setup(
            used_model, "conversation generation"
        )

        try:
            contents, system_instruction = _build_gemini_contents(messages)

            response = await gemini_client.aio.models.generate_content(
                model=base_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=settings.CONTENT_TEMPERATURE,
                    max_output_tokens=budget,
                    thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
                    media_resolution=settings.GEMINI_MEDIA_RESOLUTION,
                ),
            )
            generated = response.text or ""
            return sanitize_markdown(generated), used_model
        except Exception as e:
            logger.error(f"Error generating conversation content (Gemini): {e}", exc_info=True)
            raise handle_openai_exception(e)

    else:
        try:
            openai_client = settings.openai_client
            base_model, extra_params = _resolve_openai_model(used_model)
            api_params = {
                "model": base_model,
                "messages": messages,
                "max_completion_tokens": budget,
                "temperature": settings.CONTENT_TEMPERATURE,
            }
            api_params.update(extra_params)

            completion = await openai_client.chat.completions.create(**api_params)
            raw = completion.choices[0].message.content or ""
            return sanitize_markdown(raw), used_model
        except Exception as e:
            logger.error(f"Error generating conversation content (OpenAI): {e}", exc_info=True)
            raise handle_openai_exception(e)
