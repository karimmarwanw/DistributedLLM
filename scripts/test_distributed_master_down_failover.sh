#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

KARIM_HOST="${KARIM_HOST:-karims-macbook-pro.local}"
ADAM_HOST="${ADAM_HOST:-Adams-MacBook-Pro.local}"
LB_URL="${DISTRIBUTED_LB_URL:-http://$KARIM_HOST:8000}"
LB_QUERY_URL="${LB_QUERY_URL:-http://$KARIM_HOST:8000/query}"

restore_master0() {
  start_service master0 env SERVICE_HOST=0.0.0.0 WORKER_REQUEST_TIMEOUT=300 "$PYTHON" -m master.scheduler --master-id 0 --port 8001 --workers 0:9001 1:9002
  wait_for_http "http://127.0.0.1:8001/health" "Karim Master 0 restored" 60
}

trap restore_master0 EXIT

wait_for_http "$LB_URL/health" "Distributed load balancer"
wait_for_http "http://$ADAM_HOST:8002/health" "Adam Master 1"

set_strategy round_robin
curl -fsS -X POST "$LB_URL/simulate/reset-round-robin?index=0"
echo

echo "Stopping Karim Master 0 before the request..."
stop_service master0

echo "Sending request through distributed load balancer."
echo "Expected final master_id: 1"
LB_QUERY_URL="$LB_QUERY_URL" "$PYTHON" -m client.load_generator \
  --users 1 \
  --timeout 400 \
  --query "Explain master failover in distributed systems." \
  --full-answer \
  --max-tokens 500
