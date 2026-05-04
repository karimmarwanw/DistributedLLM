#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

USERS="${1:-100}"
QUERY="${2:-Explain distributed load balancing briefly.}"

for strategy in round_robin least_connections load_aware; do
  echo
  echo "===== Strategy: $strategy ====="
  set_strategy "$strategy"
  "$PYTHON" -m client.load_generator \
    --users "$USERS" \
    --timeout 180 \
    --query "$QUERY"
done
