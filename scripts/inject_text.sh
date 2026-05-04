#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 source_name \"document text\"" >&2
  exit 1
fi

SOURCE_NAME="$1"
shift
TEXT="$*"

"$PYTHON" -m rag.ingest \
  --rag-url "$RAG_URL" \
  --source "$SOURCE_NAME" \
  --text "$TEXT"
