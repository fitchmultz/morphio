#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "backend" / "app" / "config.py"
TEMPLATE_PATH = ROOT / ".env.example"


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


def main() -> int:
    if not CONFIG_PATH.exists():
        print(f"Config not found: {CONFIG_PATH}")
        return 1
    if not TEMPLATE_PATH.exists():
        print(f"Template not found: {TEMPLATE_PATH}")
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

    print(f"✅ Env template contains all {len(env_keys)} config keys.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
