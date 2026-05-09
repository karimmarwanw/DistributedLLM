#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

KARIM_HOST="${KARIM_HOST:-karims-macbook-pro.local}"
QUERY="${1:-why are threads useful in distributed systems?}"
MAX_TOKENS="${2:-300}"
LB_URL="${DISTRIBUTED_LB_URL:-http://$KARIM_HOST:8000}"
LB_QUERY_URL="${LB_QUERY_URL:-http://$KARIM_HOST:8000/query}"

set_strategy round_robin

LB_QUERY_URL="$LB_QUERY_URL" "$PYTHON" -m client.load_generator \
  --users 10 \
  --timeout 400 \
  --query "$QUERY" \
  --show-results \
  --result-chars 450 \
  --max-tokens "$MAX_TOKENS"
