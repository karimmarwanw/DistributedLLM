#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

"$SCRIPT_DIR/stop_system.sh"

start_ollama_service

start_service rag env QDRANT_PATH="$QDRANT_PATH" "$PYTHON" -m rag.api --port "$RAG_PORT"
wait_for_http "$RAG_URL/health" "RAG service"

start_service worker0 env USE_OLLAMA=true RAG_URL="$RAG_URL" OLLAMA_MODEL="$OLLAMA_MODEL" OLLAMA_TIMEOUT=300 OLLAMA_KEEP_ALIVE="$OLLAMA_KEEP_ALIVE" "$PYTHON" -m workers.gpu_worker --id 0 --master-id 0 --port 9001
start_service worker1 env USE_OLLAMA=true RAG_URL="$RAG_URL" OLLAMA_MODEL="$OLLAMA_MODEL" OLLAMA_TIMEOUT=300 OLLAMA_KEEP_ALIVE="$OLLAMA_KEEP_ALIVE" "$PYTHON" -m workers.gpu_worker --id 1 --master-id 1 --port 9002
wait_for_http "http://127.0.0.1:9001/health" "Worker 0"
wait_for_http "http://127.0.0.1:9002/health" "Worker 1"

start_service master0 env WORKER_REQUEST_TIMEOUT=300 "$PYTHON" -m master.scheduler --master-id 0 --port 8001 --workers 0:9001
start_service master1 env WORKER_REQUEST_TIMEOUT=300 "$PYTHON" -m master.scheduler --master-id 1 --port 8002 --workers 1:9002
wait_for_http "http://127.0.0.1:8001/health" "Master 0"
wait_for_http "http://127.0.0.1:8002/health" "Master 1"

start_service load_balancer env LB_MASTER_TIMEOUT=300 "$PYTHON" -m lb.load_balancer
wait_for_http "$LB_URL/health" "Load balancer"
set_strategy round_robin

echo "Stopping Master 0 before the request..."
stop_service master0

echo "Sending request through load balancer. Expected final master_id: 1"
"$PYTHON" -m client.load_generator \
  --users 1 \
  --timeout 400 \
  --query "Explain fault tolerance in distributed systems." \
  --full-answer \
  --max-tokens 500
show_logs_hint
