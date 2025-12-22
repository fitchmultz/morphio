import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    filename = filename.replace("\\", "/").split("/")[-1]
    filename = filename.replace("\0", "")
    filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
    return filename or "unnamed_file"


def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def utc_now() -> datetime:
    """Return timezone-aware UTC now for test usage."""
    return datetime.now(timezone.utc)
