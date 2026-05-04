#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

STOP_OLLAMA_SERVICE=false

if [[ "${1:-}" == "--stop-ollama-service" ]]; then
  STOP_OLLAMA_SERVICE=true
fi

for service in \
  load_balancer \
  master0 master1 \
  worker0 worker1 worker2 worker3 \
  rag
do
  stop_service "$service"
done

stop_stale_project_services

if [[ "$STOP_OLLAMA_SERVICE" == true ]]; then
  stop_ollama_service
else
  unload_ollama_model
fi

echo "Stopped managed services."
