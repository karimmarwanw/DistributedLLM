#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAM_RAG_URL_WAS_SET="${RAG_URL+x}"
source "$SCRIPT_DIR/lib.sh"

ADAM_MODEL="${ADAM_MODEL:-phi:2.7b}"

if [[ -z "$ADAM_RAG_URL_WAS_SET" && "$RAG_PORT" == "7000" ]]; then
  if command -v lsof >/dev/null 2>&1 && lsof -nP -tiTCP:7000 -sTCP:LISTEN >/dev/null 2>&1; then
    RAG_URL="http://127.0.0.1:7100"
    RAG_PORT=7100
    echo "Port 7000 is already in use; using Adam RAG fallback at $RAG_URL"
  fi
fi

start_ollama_service

start_service rag env SERVICE_HOST=0.0.0.0 QDRANT_PATH="$QDRANT_PATH" "$PYTHON" -m rag.api --port "$RAG_PORT"
wait_for_http "$RAG_URL/health" "Adam RAG service"

start_service worker2 env SERVICE_HOST=0.0.0.0 USE_OLLAMA=true RAG_URL="$RAG_URL" OLLAMA_MODEL="$ADAM_MODEL" OLLAMA_TIMEOUT=300 OLLAMA_KEEP_ALIVE="$OLLAMA_KEEP_ALIVE" "$PYTHON" -m workers.gpu_worker --id 2 --master-id 1 --port 9003
start_service worker3 env SERVICE_HOST=0.0.0.0 USE_OLLAMA=true RAG_URL="$RAG_URL" OLLAMA_MODEL="$ADAM_MODEL" OLLAMA_TIMEOUT=300 OLLAMA_KEEP_ALIVE="$OLLAMA_KEEP_ALIVE" "$PYTHON" -m workers.gpu_worker --id 3 --master-id 1 --port 9004

wait_for_http "http://127.0.0.1:9003/health" "Adam Worker 2"
wait_for_http "http://127.0.0.1:9004/health" "Adam Worker 3"

start_service master1 env SERVICE_HOST=0.0.0.0 WORKER_REQUEST_TIMEOUT=300 "$PYTHON" -m master.scheduler --master-id 1 --port 8002 --workers 2:9003 3:9004
wait_for_http "http://127.0.0.1:8002/health" "Adam Master 1"

echo "Adam distributed node is running."
echo "Hostname: Adams-MacBook-Pro.local"
echo "Model: $ADAM_MODEL"
echo "RAG: $RAG_URL"
echo "Master 1: http://Adams-MacBook-Pro.local:8002"
show_logs_hint
