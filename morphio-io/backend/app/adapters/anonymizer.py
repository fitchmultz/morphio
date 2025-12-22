"""
Anonymizer adapter - wraps morphio-core Anonymizer.

Provides content anonymization for PII (emails, phones, IPs, etc.).
"""

from morphio_core.security import Anonymizer, anonymize_content, deanonymize_content

__all__ = [
    "Anonymizer",
    "anonymize_content",
    "deanonymize_content",
]
