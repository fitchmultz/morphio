"""Content anonymization - delegates to Rust implementation."""

from morphio_native import anonymize as _native_anonymize


class Anonymizer:
    """Anonymizes PII content using Rust implementation."""

    def __init__(self) -> None:
        self.mapping: dict[str, str] = {}
        self.reverse_mapping: dict[str, str] = {}
        self.counters: dict[str, int] = {}  # Public attribute (matches original API)

    def anonymize(self, content: str) -> str:
        """Anonymize PII in content. Clears mappings for new content."""
        result = _native_anonymize(content)
        self.mapping = dict(result.mapping)
        self.reverse_mapping = dict(result.reverse_mapping)
        self.counters = dict(result.counters)
        return result.text

    def deanonymize(self, content: str) -> str:
        """Restore original values from anonymized content.

        IMPORTANT: Applies replacements in length-descending order to avoid
        partial matches when one placeholder is a prefix of another.
        """
        result = content
        # Sort by placeholder length descending, then by placeholder itself for determinism
        # e.g., [EMAIL_10] must be replaced before [EMAIL_1]
        sorted_items = sorted(
            self.reverse_mapping.items(), key=lambda x: (len(x[0]), x[0]), reverse=True
        )
        for placeholder, original in sorted_items:
            result = result.replace(placeholder, original)
        return result


def anonymize_content(content: str, enabled: bool = False) -> str:
    """Convenience function - DEFAULT IS FALSE (matches current API)."""
    if not enabled:
        return content
    return _native_anonymize(content).text


def deanonymize_content(content: str, anonymized_content: str, enabled: bool = False) -> str:
    """Convenience function - signature preserved exactly."""
    if not enabled:
        return anonymized_content
    result = _native_anonymize(content)
    output = anonymized_content
    # Sort by placeholder length descending, then by placeholder itself for determinism
    sorted_items = sorted(
        result.reverse_mapping.items(), key=lambda x: (len(x[0]), x[0]), reverse=True
    )
    for placeholder, original in sorted_items:
        output = output.replace(placeholder, original)
    return output
