import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)


class Anonymizer:
    def __init__(self):
        self.mapping: Dict[str, str] = {}  # original -> anonymized
        self.reverse_mapping: Dict[str, str] = {}  # anonymized -> original

    def anonymize(self, content: str) -> str:
        """Anonymize sensitive data in content, maintaining consistency."""
        # IP Addresses
        content = self._replace_pattern(content, r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "IP")
        # Emails
        content = self._replace_pattern(content, r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "EMAIL")
        # Usernames (simplified: word boundaries, adjust regex as needed)
        content = self._replace_pattern(
            content, r"\b(?<![\w\.-])[a-zA-Z0-9_-]{3,20}\b(?![\w\.-])", "USER"
        )
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
        return content

    def deanonymize(self, content: str) -> str:
        """Replace anonymized values with originals using in-memory mapping."""
        for anon_value, orig_value in self.reverse_mapping.items():
            content = content.replace(anon_value, orig_value)
        return content

    def _replace_pattern(self, content: str, pattern: str, prefix: str) -> str:
        """Replace matches of a pattern with consistent anonymized values."""

        def replace_match(match):
            original = match.group(0)
            if original not in self.mapping:
                count = len([k for k in self.mapping.keys() if k.startswith(prefix)]) + 1
                anon_value = f"{prefix}_{count}"
                self.mapping[original] = anon_value
            return self.mapping[original]

        return re.sub(pattern, replace_match, content)


def anonymize_content(content: str, enabled: bool = False) -> str:
    """Anonymize content if enabled."""
    if not enabled:
        return content
    anonymizer = Anonymizer()
    return anonymizer.anonymize(content)


def deanonymize_content(content: str, anonymized_content: str, enabled: bool = False) -> str:
    """De-anonymize content if enabled, using the anonymized version to rebuild mapping."""
    if not enabled:
        return content
    anonymizer = Anonymizer()
    anonymizer.anonymize(anonymized_content)  # Rebuild mapping
    return anonymizer.deanonymize(content)
