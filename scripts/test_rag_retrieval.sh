#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

QUERY="${*:-what is process context?}"

curl -fsS --get "$RAG_URL/retrieve" --data-urlencode "query=$QUERY"
echo
