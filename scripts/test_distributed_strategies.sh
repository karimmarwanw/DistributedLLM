#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

KARIM_HOST="${KARIM_HOST:-karims-macbook-pro.local}"
USERS="${1:-10}"
QUERY="${2:-Explain distributed load balancing briefly.}"
LB_URL="${DISTRIBUTED_LB_URL:-http://$KARIM_HOST:8000}"
LB_QUERY_URL="${LB_QUERY_URL:-http://$KARIM_HOST:8000/query}"

for strategy in round_robin least_connections load_aware; do
  echo
  echo "===== Distributed strategy: $strategy ====="
  set_strategy "$strategy"

  LB_QUERY_URL="$LB_QUERY_URL" "$PYTHON" -m client.load_generator \
    --users "$USERS" \
    --timeout 400 \
    --query "$QUERY"
done

set_strategy round_robin
