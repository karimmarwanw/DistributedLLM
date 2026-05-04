#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

start_ollama_service

start_service rag env QDRANT_PATH="$QDRANT_PATH" "$PYTHON" -m rag.api --port 7000
wait_for_http "$RAG_URL/health" "RAG service"

start_service worker0 env USE_OLLAMA=true RAG_URL="$RAG_URL" OLLAMA_MODEL="$OLLAMA_MODEL" OLLAMA_TIMEOUT=300 OLLAMA_KEEP_ALIVE="$OLLAMA_KEEP_ALIVE" "$PYTHON" -m workers.gpu_worker --id 0 --master-id 0 --port 9001
start_service worker1 env USE_OLLAMA=true RAG_URL="$RAG_URL" OLLAMA_MODEL="$OLLAMA_MODEL" OLLAMA_TIMEOUT=300 OLLAMA_KEEP_ALIVE="$OLLAMA_KEEP_ALIVE" "$PYTHON" -m workers.gpu_worker --id 1 --master-id 0 --port 9002
start_service worker2 env USE_OLLAMA=true RAG_URL="$RAG_URL" OLLAMA_MODEL="$OLLAMA_MODEL" OLLAMA_TIMEOUT=300 OLLAMA_KEEP_ALIVE="$OLLAMA_KEEP_ALIVE" "$PYTHON" -m workers.gpu_worker --id 2 --master-id 1 --port 9003
start_service worker3 env USE_OLLAMA=true RAG_URL="$RAG_URL" OLLAMA_MODEL="$OLLAMA_MODEL" OLLAMA_TIMEOUT=300 OLLAMA_KEEP_ALIVE="$OLLAMA_KEEP_ALIVE" "$PYTHON" -m workers.gpu_worker --id 3 --master-id 1 --port 9004

wait_for_http "http://127.0.0.1:9001/health" "Worker 0"
wait_for_http "http://127.0.0.1:9002/health" "Worker 1"
wait_for_http "http://127.0.0.1:9003/health" "Worker 2"
wait_for_http "http://127.0.0.1:9004/health" "Worker 3"

start_service master0 env WORKER_REQUEST_TIMEOUT=300 "$PYTHON" -m master.scheduler --master-id 0 --port 8001 --workers 0:9001 1:9002
start_service master1 env WORKER_REQUEST_TIMEOUT=300 "$PYTHON" -m master.scheduler --master-id 1 --port 8002 --workers 2:9003 3:9004

wait_for_http "http://127.0.0.1:8001/health" "Master 0"
wait_for_http "http://127.0.0.1:8002/health" "Master 1"

start_service load_balancer env LB_MASTER_TIMEOUT=300 "$PYTHON" -m lb.load_balancer
wait_for_http "$LB_URL/health" "Load balancer"
set_strategy round_robin

echo "Ollama system is running with model: $OLLAMA_MODEL"
show_logs_hint
