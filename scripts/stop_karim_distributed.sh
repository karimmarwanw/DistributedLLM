#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KARIM_MODEL="${KARIM_MODEL:-llama3.2:1b}"

OLLAMA_MODEL="$KARIM_MODEL" "$SCRIPT_DIR/stop_system.sh" "$@"
