#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

KARIM_HOST="${KARIM_HOST:-karims-macbook-pro.local}"
ADAM_HOST="${ADAM_HOST:-Adams-MacBook-Pro.local}"
KARIM_MODEL="${KARIM_MODEL:-llama3.2:1b}"
DISTRIBUTED_MASTER_URLS="${MASTER_URLS:-0:http://$KARIM_HOST:8001,1:http://$ADAM_HOST:8002}"

start_ollama_service

start_service rag env SERVICE_HOST=0.0.0.0 QDRANT_PATH="$QDRANT_PATH" "$PYTHON" -m rag.api --port "$RAG_PORT"
wait_for_http "$RAG_URL/health" "Karim RAG service"

start_service worker0 env SERVICE_HOST=0.0.0.0 USE_OLLAMA=true RAG_URL="$RAG_URL" OLLAMA_MODEL="$KARIM_MODEL" OLLAMA_TIMEOUT=300 OLLAMA_KEEP_ALIVE="$OLLAMA_KEEP_ALIVE" "$PYTHON" -m workers.gpu_worker --id 0 --master-id 0 --port 9001
start_service worker1 env SERVICE_HOST=0.0.0.0 USE_OLLAMA=true RAG_URL="$RAG_URL" OLLAMA_MODEL="$KARIM_MODEL" OLLAMA_TIMEOUT=300 OLLAMA_KEEP_ALIVE="$OLLAMA_KEEP_ALIVE" "$PYTHON" -m workers.gpu_worker --id 1 --master-id 0 --port 9002

wait_for_http "http://127.0.0.1:9001/health" "Karim Worker 0"
wait_for_http "http://127.0.0.1:9002/health" "Karim Worker 1"

start_service master0 env SERVICE_HOST=0.0.0.0 WORKER_REQUEST_TIMEOUT=300 "$PYTHON" -m master.scheduler --master-id 0 --port 8001 --workers 0:9001 1:9002
wait_for_http "http://127.0.0.1:8001/health" "Karim Master 0"
wait_for_http "http://$ADAM_HOST:8002/health" "Adam Master 1"

start_service load_balancer env SERVICE_HOST=0.0.0.0 MASTER_URLS="$DISTRIBUTED_MASTER_URLS" LB_MASTER_TIMEOUT=300 "$PYTHON" -m lb.load_balancer
wait_for_http "$LB_URL/health" "Distributed load balancer"
set_strategy round_robin

echo "Karim distributed coordinator is running."
echo "Karim hostname: $KARIM_HOST"
echo "Adam hostname: $ADAM_HOST"
echo "Karim model: $KARIM_MODEL"
echo "Master URLs: $DISTRIBUTED_MASTER_URLS"
echo "Load balancer: http://$KARIM_HOST:8000"
show_logs_hint
