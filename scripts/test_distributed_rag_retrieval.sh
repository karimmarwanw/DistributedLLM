#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

KARIM_HOST="${KARIM_HOST:-karims-macbook-pro.local}"
ADAM_HOST="${ADAM_HOST:-Adams-MacBook-Pro.local}"
KARIM_RAG_URL="${KARIM_RAG_URL:-http://$KARIM_HOST:7100}"
ADAM_RAG_URL="${ADAM_RAG_URL:-http://$ADAM_HOST:7100}"
QUERY="${*:-what is process context?}"

echo "Karim RAG:"
curl -fsS --get "$KARIM_RAG_URL/retrieve" --data-urlencode "query=$QUERY"
echo
echo

echo "Adam RAG:"
curl -fsS --get "$ADAM_RAG_URL/retrieve" --data-urlencode "query=$QUERY"
echo
