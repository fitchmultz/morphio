#!/usr/bin/env bash
# Audit provider SDK imports in morphio-io/backend/
#
# This script enforces the architecture boundary: provider SDKs (openai, anthropic,
# google.genai) should only be imported in morphio-core, not directly in morphio-io.
#
# The backend should use morphio-core via adapters (app/adapters/), not import
# provider SDKs directly.
#
# Scope:
#   - app/ - main backend application
#   - worker_ml/ - ML worker service
#   - crawler/ - web crawler service
#
# Exceptions:
#   - app/config.py is allowed (deprecated client properties with deprecation notices)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_ROOT="$REPO_ROOT/morphio-io/backend"

# Directories to audit
AUDIT_DIRS=(
    "$BACKEND_ROOT/app"
    "$BACKEND_ROOT/worker_ml"
    "$BACKEND_ROOT/crawler"
)

# List of banned import patterns
BANNED_PATTERNS=(
    "^from openai import"
    "^import openai"
    "^from anthropic import"
    "^import anthropic"
    "^from google import genai"
    "^from google.genai import"
    "^import google.genai"
)

# Files to skip (exceptions with documentation)
SKIP_FILES=(
    "app/config.py"  # Contains deprecated client properties with RuntimeError
    "app/utils/error_handlers.py"  # Catches SDK exceptions from morphio-core adapter calls
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Auditing provider SDK imports in morphio-io/backend/..."
echo "   Directories: app/, worker_ml/, crawler/"
echo ""

VIOLATIONS=0

for audit_dir in "${AUDIT_DIRS[@]}"; do
    # Skip if directory doesn't exist
    [[ -d "$audit_dir" ]] || continue

    for pattern in "${BANNED_PATTERNS[@]}"; do
        # Search for the pattern in Python files, excluding exceptions
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                # Extract filename from grep output
                file=$(echo "$line" | cut -d: -f1)
                rel_file="${file#$BACKEND_ROOT/}"

                # Check if file is in skip list
                skip=false
                for skip_file in "${SKIP_FILES[@]}"; do
                    if [[ "$rel_file" == "$skip_file" ]]; then
                        skip=true
                        break
                    fi
                done

                if [[ "$skip" == "false" ]]; then
                    echo -e "${RED}❌ VIOLATION:${NC} $line"
                    ((VIOLATIONS++))
                else
                    echo -e "${YELLOW}⚠️  ALLOWED (deprecated):${NC} $rel_file"
                fi
            fi
        done < <(grep -rn --include="*.py" -E "$pattern" "$audit_dir" 2>/dev/null || true)
    done
done

echo ""

if [[ $VIOLATIONS -gt 0 ]]; then
    echo -e "${RED}❌ Found $VIOLATIONS provider SDK import violation(s)!${NC}"
    echo ""
    echo "Provider SDKs should be imported in morphio-core, not morphio-io."
    echo "Use the adapters in app/adapters/ to access morphio-core functionality."
    echo ""
    echo "See docs/architecture.md for the adapter boundary documentation."
    exit 1
else
    echo -e "${GREEN}✅ No provider SDK import violations found!${NC}"
    exit 0
fi
