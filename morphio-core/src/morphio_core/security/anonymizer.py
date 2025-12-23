"""
Content anonymization utilities.

Pure regex-based PII anonymization with reversible mappings.
"""

import ipaddress
import logging
import re

logger = logging.getLogger(__name__)


class Anonymizer:
    """
    Anonymizes and de-anonymizes content by replacing patterns with placeholders.

    Patterns handled:
    - Email addresses
    - Phone numbers
    - Credit card numbers
    - Social security numbers
    - IP addresses
    """

    def __init__(self):
        self.mapping: dict[str, str] = {}
        self.reverse_mapping: dict[str, str] = {}
        self.counters: dict[str, int] = {}

    def anonymize(self, content: str) -> str:
        """
        Anonymize PII in content.

        Args:
            content: Text to anonymize

        Returns:
            Anonymized text with placeholders
        """
        # Clear mappings for new content
        self.mapping = {}
        self.reverse_mapping = {}
        self.counters = {}

        # Email addresses
        content = self._replace_pattern(
            content, r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "EMAIL"
        )

        # Phone numbers (various formats)
        content = self._replace_pattern(
            content,
            r"(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}",
            "PHONE",
        )

        # Credit card numbers
        content = self._replace_pattern(content, r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "CREDIT_CARD")

        # Social security numbers
        content = self._replace_pattern(content, r"\b\d{3}-\d{2}-\d{4}\b", "SSN")

        # IP addresses (validated with ipaddress module)
        content = self._replace_valid_ips(content)

        return content

    def deanonymize(self, content: str) -> str:
        """
        Restore original values from anonymized content.

        Args:
            content: Anonymized text with placeholders

        Returns:
            Original text with PII restored
        """
        result = content
        for placeholder, original in self.reverse_mapping.items():
            result = result.replace(placeholder, original)
        return result

    def _replace_pattern(self, content: str, pattern: str, prefix: str) -> str:
        """Replace matches of pattern with numbered placeholders."""
        if prefix not in self.counters:
            self.counters[prefix] = 0

        def replace_match(match):
            original = match.group(0)
            if original in self.mapping:
                return self.mapping[original]

            self.counters[prefix] += 1
            placeholder = f"[{prefix}_{self.counters[prefix]}]"
            self.mapping[original] = placeholder
            self.reverse_mapping[placeholder] = original
            return placeholder

        return re.sub(pattern, replace_match, content)

    def _replace_valid_ips(self, content: str) -> str:
        """Replace valid IPv4 addresses with placeholders.

        Uses the ipaddress module to validate IPs, ensuring only
        valid addresses (0-255 per octet) are anonymized.
        """
        prefix = "IP_ADDRESS"
        if prefix not in self.counters:
            self.counters[prefix] = 0

        # Match IP-like patterns, then validate each
        pattern = r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b"

        def replace_if_valid(match: re.Match) -> str:
            ip = match.group(1)

            # Validate with ipaddress module
            try:
                ipaddress.IPv4Address(ip)
            except ipaddress.AddressValueError:
                # Invalid IP - leave unchanged
                return ip

            # Already mapped
            if ip in self.mapping:
                return self.mapping[ip]

            # Create new placeholder
            self.counters[prefix] += 1
            placeholder = f"[{prefix}_{self.counters[prefix]}]"
            self.mapping[ip] = placeholder
            self.reverse_mapping[placeholder] = ip
            return placeholder

        return re.sub(pattern, replace_if_valid, content)


def anonymize_content(content: str, enabled: bool = False) -> str:
    """
    Convenience function to anonymize content.

    Args:
        content: Text to anonymize
        enabled: Whether anonymization is enabled (returns unchanged if False)

    Returns:
        Anonymized text if enabled, otherwise original text
    """
    if not enabled:
        return content
    anonymizer = Anonymizer()
    return anonymizer.anonymize(content)


def deanonymize_content(content: str, anonymized_content: str, enabled: bool = False) -> str:
    """
    Convenience function to deanonymize content.

    Note: This function requires re-anonymizing the original content to rebuild
    the mapping. For better performance with multiple operations, use the
    Anonymizer class directly.

    Args:
        content: Original text (used to rebuild mapping)
        anonymized_content: Text with placeholders to deanonymize
        enabled: Whether deanonymization is enabled

    Returns:
        Deanonymized text if enabled, otherwise anonymized_content unchanged
    """
    if not enabled:
        return anonymized_content

    # Rebuild mapping by re-anonymizing original
    anonymizer = Anonymizer()
    anonymizer.anonymize(content)

    # Apply reverse mapping
    return anonymizer.deanonymize(anonymized_content)
