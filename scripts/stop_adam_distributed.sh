#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAM_MODEL="${ADAM_MODEL:-phi:2.7b}"

OLLAMA_MODEL="$ADAM_MODEL" "$SCRIPT_DIR/stop_system.sh" "$@"
