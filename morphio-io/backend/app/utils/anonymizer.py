"""
Content anonymization utilities - re-exports from morphio-core adapter.

This module maintains backward compatibility with existing imports.
The morphio-core Anonymizer handles: EMAIL, PHONE, CREDIT_CARD, SSN, IP_ADDRESS.
"""

from ..adapters.anonymizer import (
    Anonymizer,
    anonymize_content,
    deanonymize_content,
)

__all__ = [
    "Anonymizer",
    "anonymize_content",
    "deanonymize_content",
]
