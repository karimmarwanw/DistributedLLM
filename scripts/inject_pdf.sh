#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/document.pdf [source_name]" >&2
  exit 1
fi

PDF_PATH="$1"
SOURCE_NAME="${2:-$(basename "$PDF_PATH")}"

"$PYTHON" -m rag.ingest \
  --rag-url "$RAG_URL" \
  --source "$SOURCE_NAME" \
  --file "$PDF_PATH"
