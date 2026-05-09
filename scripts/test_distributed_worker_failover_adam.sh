#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

ADAM_HOST="${ADAM_HOST:-Adams-MacBook-Pro.local}"

wait_for_http "http://$ADAM_HOST:8002/health" "Adam Master 1"
wait_for_http "http://$ADAM_HOST:9003/health" "Adam Worker 2"
wait_for_http "http://$ADAM_HOST:9004/health" "Adam Worker 3"

echo "Resetting Master 1 worker round robin to Worker 2..."
curl -fsS -X POST "http://$ADAM_HOST:8002/simulate/reset-worker-round-robin?index=0"
echo

echo "Forcing Adam Worker 2 to fail during its next request..."
curl -fsS -X POST "http://$ADAM_HOST:9003/simulate/fail-next?delay=2&reason=distributed%20worker%202%20failure"
echo

echo "Sending request directly to Adam Master 1."
echo "Expected final worker_id: 3"
curl -fsS -X POST "http://$ADAM_HOST:8002/schedule" \
  -H "Content-Type: application/json" \
  -d '{"id":991,"query":"Explain worker failover in distributed systems.","max_tokens":300}'
echo
