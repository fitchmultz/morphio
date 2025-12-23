"""
morphio-core CLI.

Provides command-line utilities for audio transcription, URL validation,
and video downloading.

Install with: uv add morphio-core[cli]
"""

import importlib.util

if importlib.util.find_spec("typer") is None or importlib.util.find_spec("rich") is None:
    raise ImportError("CLI dependencies not installed. Install with: uv add morphio-core[cli]")

from .main import app

__all__ = ["app"]
