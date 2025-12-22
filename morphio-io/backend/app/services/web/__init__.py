"""
Web module for scraping and processing web content.
"""

from .job import (
    enqueue_web_scraping,
    get_web_processing_status,
)
from .operations import (
    scrape_and_generate_web,
    scrape_webpage,
)
from .validation import is_private_or_local_address

__all__ = [
    "enqueue_web_scraping",
    "get_web_processing_status",
    "scrape_and_generate_web",
    "scrape_webpage",
    "is_private_or_local_address",
]
