"""Purpose: Regression tests for generation-core model selection.
Responsibilities: Ensure title generation falls back cleanly when stale model aliases remain in config.
Scope: Unit coverage for title-generation model resolution in the backend generation service.
Usage: Executed by pytest in the backend unit suite.
Invariants/Assumptions: Invalid title-model config must not break otherwise successful content generation flows.
"""

import pytest

from app.services.generation import core


@pytest.mark.asyncio
async def test_generate_content_title_falls_back_from_invalid_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core.settings, "TITLE_GENERATION_MODEL", "gpt-4o", raising=False)
    monkeypatch.setattr(
        core.settings,
        "CONTENT_MODEL",
        "gemini-3-flash-preview-minimal",
        raising=False,
    )

    captured: dict[str, str | int] = {}

    async def fake_generate_completion(*, messages, model, max_tokens):
        captured["model"] = model
        captured["message_count"] = len(messages)
        captured["max_tokens"] = max_tokens
        return "Recovered Title", model

    monkeypatch.setattr(core, "generate_completion", fake_generate_completion)

    title = await core.generate_content_title("hello world")

    assert title == "Recovered Title"
    assert captured["model"] == "gemini-3-flash-preview-minimal"
    assert captured["message_count"] == 2
    assert captured["max_tokens"] == 35


@pytest.mark.asyncio
async def test_generate_content_from_transcript_falls_back_from_invalid_default_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core.settings, "CONTENT_MODEL", "gpt-4o", raising=False)

    captured: dict[str, str | int] = {}

    async def fake_generate_completion(*, messages, model, max_tokens):
        captured["model"] = model
        captured["message_count"] = len(messages)
        captured["max_tokens"] = max_tokens
        return "Generated markdown", model

    monkeypatch.setattr(core, "generate_completion", fake_generate_completion)

    output = await core.generate_content_from_transcript(
        transcript="sample transcript",
        template_content="Summarize this transcript.",
        chosen_model="",
    )

    assert output == "Generated markdown"
    assert captured["model"] == "gemini-3-flash-preview-minimal"
    assert captured["message_count"] == 2
