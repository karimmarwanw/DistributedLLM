#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

KARIM_HOST="${KARIM_HOST:-karims-macbook-pro.local}"
USERS="${1:-10}"
QUERY="${2:-What is distributed computing?}"
MAX_TOKENS="${3:-180}"
LB_QUERY_URL="${LB_QUERY_URL:-http://$KARIM_HOST:8000/query}"

LB_QUERY_URL="$LB_QUERY_URL" "$PYTHON" -m client.load_generator \
  --users "$USERS" \
  --timeout 400 \
  --query "$QUERY" \
  --max-tokens "$MAX_TOKENS"
