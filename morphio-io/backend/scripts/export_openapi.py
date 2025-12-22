#!/usr/bin/env python3
"""Export OpenAPI schema without running the server.

This script imports the FastAPI app and extracts the OpenAPI schema directly,
avoiding the need for a running server. The schema is written to stdout or
a specified file path.

Usage:
    python scripts/export_openapi.py                    # Output to stdout
    python scripts/export_openapi.py -o openapi.json   # Output to file
    python scripts/export_openapi.py --output ../frontend/openapi.json
"""

import argparse
import json
import sys
from pathlib import Path


def export_openapi(output_path: str | None = None) -> None:
    """Export OpenAPI schema from the FastAPI app."""
    # Import here to avoid side effects at module level
    from app.main import app

    schema = app.openapi()

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(schema, f, indent="\t")
        print(f"OpenAPI schema exported to {path}", file=sys.stderr)
    else:
        json.dump(schema, sys.stdout, indent="\t")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export OpenAPI schema from FastAPI app")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    args = parser.parse_args()

    export_openapi(args.output)


if __name__ == "__main__":
    main()
