#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

KARIM_HOST="${KARIM_HOST:-karims-macbook-pro.local}"
ADAM_HOST="${ADAM_HOST:-Adams-MacBook-Pro.local}"

check_url() {
  local name="$1"
  local url="$2"

  printf "%-28s %s ... " "$name" "$url"

  if curl -fsS "$url" >/dev/null 2>&1; then
    echo "OK"
  else
    echo "FAILED"
  fi
}

check_url "Karim load balancer" "http://$KARIM_HOST:8000/health"
check_url "Karim master 0" "http://$KARIM_HOST:8001/health"
check_url "Karim RAG" "http://$KARIM_HOST:7000/health"
check_url "Adam master 1" "http://$ADAM_HOST:8002/health"
check_url "Adam RAG" "http://$ADAM_HOST:7000/health"
