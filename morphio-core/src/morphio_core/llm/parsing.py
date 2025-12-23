"""LLM output parsing and sanitization utilities."""

import re


def sanitize_markdown(content: str) -> str:
    """Ensure code blocks are properly closed and escape stray backticks.

    LLMs sometimes produce malformed markdown with unclosed code blocks
    or stray backticks that break rendering. This function fixes common issues.

    Args:
        content: Raw markdown content from LLM

    Returns:
        Sanitized markdown with properly closed code blocks

    Example:
        # Unclosed code block gets closed
        content = '''```python
        def hello():
            print("world")
        '''
        sanitize_markdown(content)
        # Returns: '''```python
        # def hello():
        #     print("world")
        # ```'''
    """
    # Find all code blocks (including unclosed ones)
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


def strip_code_fences(content: str) -> str:
    """Remove markdown code fence wrappers from content.

    Useful when LLM wraps response in code fences but you want raw content.

    Args:
        content: Content that may be wrapped in code fences

    Returns:
        Content with outer code fences removed

    Example:
        content = '''```json
        {"key": "value"}
        ```'''
        strip_code_fences(content)
        # Returns: '{"key": "value"}'
    """
    content = content.strip()

    # Check if content starts with code fence
    if not content.startswith("```"):
        return content

    # Remove opening fence (with optional language tag)
    content = re.sub(r"^```\w*\n?", "", content, count=1)

    # Remove closing fence
    content = re.sub(r"\n?```$", "", content)

    return content.strip()


def extract_json_from_response(content: str) -> str:
    """Extract JSON from LLM response that may include explanation text.

    LLMs often include explanations before/after JSON. This extracts
    the JSON portion, handling both fenced and unfenced JSON.

    Args:
        content: LLM response that contains JSON

    Returns:
        Extracted JSON string

    Example:
        content = '''Here's the JSON:
        ```json
        {"name": "test"}
        ```
        Let me know if you need changes.'''
        extract_json_from_response(content)
        # Returns: '{"name": "test"}'
    """
    # First try to find fenced JSON
    fenced_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", content)
    if fenced_match:
        return fenced_match.group(1).strip()

    # Try to find JSON object or array (non-greedy to match first complete JSON)
    json_match = re.search(r"(\{[\s\S]*?\}|\[[\s\S]*?\])", content)
    if json_match:
        return json_match.group(1).strip()

    # Return original content if no JSON found
    return content.strip()


def truncate_for_context(
    content: str,
    max_chars: int,
    *,
    suffix: str = "...[truncated]",
) -> str:
    """Truncate content to fit within context limits.

    Truncates at a word boundary when possible to avoid cutting words.

    Args:
        content: Content to truncate
        max_chars: Maximum character count
        suffix: Suffix to append when truncated

    Returns:
        Truncated content with suffix if truncated

    Example:
        content = "This is a long piece of content"
        truncate_for_context(content, 20)
        # Returns: "This is a...[truncated]"
    """
    if len(content) <= max_chars:
        return content

    # Account for suffix length
    target_len = max_chars - len(suffix)
    if target_len <= 0:
        return suffix[:max_chars]

    # Find last space before target length
    truncated = content[:target_len]
    last_space = truncated.rfind(" ")

    if last_space > target_len // 2:
        # Truncate at word boundary
        return truncated[:last_space] + suffix

    # No good word boundary, hard truncate
    return truncated + suffix
