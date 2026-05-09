#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

KARIM_HOST="${KARIM_HOST:-karims-macbook-pro.local}"
ADAM_HOST="${ADAM_HOST:-Adams-MacBook-Pro.local}"
LB_URL="${DISTRIBUTED_LB_URL:-http://$KARIM_HOST:8000}"
LB_QUERY_URL="${LB_QUERY_URL:-http://$KARIM_HOST:8000/query}"

restore_master0() {
  stop_service master0
  start_service master0 env SERVICE_HOST=0.0.0.0 WORKER_REQUEST_TIMEOUT=300 "$PYTHON" -m master.scheduler --master-id 0 --port 8001 --workers 0:9001 1:9002
  wait_for_http "http://127.0.0.1:8001/health" "Karim Master 0 restored" 60
}

trap restore_master0 EXIT

wait_for_http "$LB_URL/health" "Distributed load balancer"
wait_for_http "http://$KARIM_HOST:9001/health" "Karim Worker 0"
wait_for_http "http://$KARIM_HOST:9002/health" "Karim Worker 1"
wait_for_http "http://$ADAM_HOST:8002/health" "Adam Master 1"

echo "Temporarily restarting Karim Master 0 with only Worker 0 registered..."
stop_service master0
start_service master0 env SERVICE_HOST=0.0.0.0 WORKER_REQUEST_TIMEOUT=300 "$PYTHON" -m master.scheduler --master-id 0 --port 8001 --workers 0:9001
wait_for_http "http://127.0.0.1:8001/health" "Karim Master 0 single-worker mode" 60

set_strategy round_robin
curl -fsS -X POST "$LB_URL/simulate/reset-round-robin?index=0"
echo

echo "Forcing Karim's only registered worker to fail..."
curl -fsS -X POST "http://$KARIM_HOST:9001/simulate/fail-next?delay=2&reason=only%20registered%20worker%20under%20master%200%20failed"
echo

echo "Sending request through distributed load balancer."
echo "Expected behavior: Master 0 stays alive but cannot complete, then load balancer retries Master 1."
echo "Expected final master_id: 1"
LB_QUERY_URL="$LB_QUERY_URL" "$PYTHON" -m client.load_generator \
  --users 1 \
  --timeout 400 \
  --query "Explain worker failure recovery in distributed systems." \
  --full-answer \
  --max-tokens 700
