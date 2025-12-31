#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MONOREPO_ROOT = ROOT.parent
CONFIG_PATH = ROOT / "backend" / "app" / "config.py"
TEMPLATE_PATH = MONOREPO_ROOT / ".env.example"
FRONTEND_PATH = ROOT / "frontend"
FRONTEND_FILES = [
    FRONTEND_PATH / "next.config.ts",
]
COMPOSE_FILES = [
    ROOT / "docker-compose.yml",
    ROOT / "docker-compose.watch.yml",
    ROOT / "docker-compose.prod.yml",
    ROOT / "docker-compose.staging.yml",
]


def extract_env_keys(config_text: str) -> set[str]:
    keys = set(re.findall(r'"env"\s*:\s*"([^"]+)"', config_text))
    keys.update(re.findall(r'validation_alias="([^"]+)"', config_text))
    for match in re.findall(r"AliasChoices\(([^)]*)\)", config_text):
        keys.update(re.findall(r'"([^"]+)"', match))
    return keys


def extract_template_keys(template_text: str) -> set[str]:
    keys: set[str] = set()
    for line in template_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key:
            keys.add(key)
    return keys


def extract_frontend_env_keys() -> set[str]:
    keys: set[str] = set()
    src_path = FRONTEND_PATH / "src"
    if src_path.exists():
        for path in src_path.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            keys.update(re.findall(r"NEXT_PUBLIC_[A-Z0-9_]+", text))
    for path in FRONTEND_FILES:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        keys.update(re.findall(r"NEXT_PUBLIC_[A-Z0-9_]+", text))
    return keys


def extract_compose_vars(compose_text: str) -> tuple[set[str], set[str]]:
    with_defaults: set[str] = set()
    without_defaults: set[str] = set()
    for match in re.finditer(r"\$\{([A-Z0-9_]+)([^}]*)\}", compose_text):
        name = match.group(1)
        suffix = match.group(2) or ""
        if suffix.startswith(":-") or suffix.startswith("-") or suffix.startswith(":?"):
            with_defaults.add(name)
        else:
            without_defaults.add(name)
    return with_defaults, without_defaults


def main() -> int:
    if not CONFIG_PATH.exists():
        print(f"Config not found: {CONFIG_PATH}")
        return 1
    if not TEMPLATE_PATH.exists():
        print(f"Template not found: {TEMPLATE_PATH}")
        return 1

    nested_env_files = sorted(
        path for path in ROOT.rglob(".env*") if path.is_file()
    )
    if nested_env_files:
        print("Only /.env and /.env.example are allowed.")
        print("Found nested env file(s):")
        for path in nested_env_files:
            print(f"- {path}")
        return 1

    root_env_local = MONOREPO_ROOT / ".env.local"
    if root_env_local.exists():
        print("Only /.env and /.env.example are allowed.")
        print(f"Found forbidden env file: {root_env_local}")
        return 1

    config_text = CONFIG_PATH.read_text(encoding="utf-8")
    template_text = TEMPLATE_PATH.read_text(encoding="utf-8")

    env_keys = extract_env_keys(config_text)
    template_keys = extract_template_keys(template_text)

    missing = sorted(env_keys - template_keys)
    if missing:
        print("Missing env keys in template:")
        for key in missing:
            print(f"- {key}")
        return 1

    frontend_keys = extract_frontend_env_keys()
    frontend_missing = sorted(frontend_keys - template_keys)
    if frontend_missing:
        print("Missing NEXT_PUBLIC_* keys in template:")
        for key in frontend_missing:
            print(f"- {key}")
        return 1

    template_next_public = {k for k in template_keys if k.startswith("NEXT_PUBLIC_")}
    unused_next_public = sorted(template_next_public - frontend_keys)
    if unused_next_public:
        print("Unused NEXT_PUBLIC_* keys in template (remove from .env.example):")
        for key in unused_next_public:
            print(f"- {key}")
        return 1

    compose_missing: set[str] = set()
    for compose_file in COMPOSE_FILES:
        if not compose_file.exists():
            continue
        compose_text = compose_file.read_text(encoding="utf-8")
        _, without_defaults = extract_compose_vars(compose_text)
        compose_missing.update(without_defaults - template_keys)
    if compose_missing:
        print("Missing compose vars without defaults in template:")
        for key in sorted(compose_missing):
            print(f"- {key}")
        return 1

    print(f"✅ Env template contains all {len(env_keys)} config keys.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
