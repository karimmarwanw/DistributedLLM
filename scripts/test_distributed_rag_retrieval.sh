#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

KARIM_HOST="${KARIM_HOST:-karims-macbook-pro.local}"
ADAM_HOST="${ADAM_HOST:-Adams-MacBook-Pro.local}"
QUERY="${*:-what is process context?}"

echo "Karim RAG:"
curl -fsS --get "http://$KARIM_HOST:7000/retrieve" --data-urlencode "query=$QUERY"
echo
echo

echo "Adam RAG:"
curl -fsS --get "http://$ADAM_HOST:7000/retrieve" --data-urlencode "query=$QUERY"
echo
