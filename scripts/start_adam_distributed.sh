#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

ADAM_MODEL="${ADAM_MODEL:-phi:2.7b}"

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
echo "Master 1: http://Adams-MacBook-Pro.local:8002"
show_logs_hint
