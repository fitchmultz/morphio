import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

from ..config import settings
from .log_context import get_correlation_id


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Preserve explicit correlation_id if provided, else from ContextVar
        corr = getattr(record, "correlation_id", None) or get_correlation_id()
        setattr(record, "correlation_id", corr or "-")
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }

        # Include location for easier debugging (cheap in dev, useful in prod)
        base.update(
            {
                "module": record.module,
                "func": record.funcName,
                "line": record.lineno,
            }
        )

        # Uvicorn access log extras
        for key in ("client_addr", "request_line", "status_code"):
            if hasattr(record, key):
                base[key] = getattr(record, key)

        # Attach any extra dict provided under `extra={"details": {...}}`
        details = getattr(record, "details", None)
        if isinstance(details, dict):
            base["details"] = details

        return json.dumps(base, ensure_ascii=False)


def _build_handlers(log_level: int):
    log_dir = os.path.join(os.getcwd(), "log_files")
    os.makedirs(log_dir, exist_ok=True)

    json_formatter = JSONFormatter()
    corr_filter = CorrelationIdFilter()

    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(json_formatter)
    console.addFilter(corr_filter)

    file_handler = logging.FileHandler(os.path.join(log_dir, "application.log"))
    file_handler.setLevel(log_level)
    file_handler.setFormatter(json_formatter)
    file_handler.addFilter(corr_filter)

    return console, file_handler


def configure_logging() -> None:
    """Configure root + uvicorn loggers with JSON output and correlation IDs."""
    log_level = getattr(logging, settings.LOG_LEVEL)

    console_handler, file_handler = _build_handlers(log_level)

    # Root logger
    root = logging.getLogger()
    root.handlers = []
    root.setLevel(log_level)
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    # Uvicorn loggers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True  # bubble up to root to use our JSON handlers
        lg.setLevel(log_level)
