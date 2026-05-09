#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

KARIM_HOST="${KARIM_HOST:-karims-macbook-pro.local}"

wait_for_http "http://$KARIM_HOST:8001/health" "Karim Master 0"
wait_for_http "http://$KARIM_HOST:9001/health" "Karim Worker 0"
wait_for_http "http://$KARIM_HOST:9002/health" "Karim Worker 1"

echo "Resetting Master 0 worker round robin to Worker 0..."
curl -fsS -X POST "http://$KARIM_HOST:8001/simulate/reset-worker-round-robin?index=0"
echo

echo "Forcing Karim Worker 0 to fail during its next request..."
curl -fsS -X POST "http://$KARIM_HOST:9001/simulate/fail-next?delay=2&reason=distributed%20worker%200%20failure"
echo

echo "Sending request directly to Karim Master 0."
echo "Expected final worker_id: 1"
curl -fsS -X POST "http://$KARIM_HOST:8001/schedule" \
  -H "Content-Type: application/json" \
  -d '{"id":990,"query":"Explain worker failover in distributed systems.","max_tokens":300}'
echo
