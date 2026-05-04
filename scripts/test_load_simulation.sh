#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

USERS="${1:-1000}"
QUERY="${2:-What is distributed computing?}"

"$PYTHON" -m client.load_generator \
  --users "$USERS" \
  --timeout 180 \
  --query "$QUERY"
