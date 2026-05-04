#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

QUERY="${1:-why are threads useful in distributed systems?}"
MAX_TOKENS="${2:-900}"

"$PYTHON" -m client.load_generator \
  --users 1 \
  --timeout 400 \
  --query "$QUERY" \
  --full-answer \
  --max-tokens "$MAX_TOKENS"
