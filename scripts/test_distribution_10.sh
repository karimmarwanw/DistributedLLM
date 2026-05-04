#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

QUERY="${1:-Explain distributed load balancing briefly.}"

set_strategy round_robin
"$PYTHON" -m client.load_generator \
  --users 10 \
  --timeout 120 \
  --query "$QUERY"
