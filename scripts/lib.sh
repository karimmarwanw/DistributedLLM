#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

url_port() {
  local url="$1"
  local after_scheme="${url#*://}"
  local host_port="${after_scheme%%/*}"
  local port="${host_port##*:}"

  if [[ "$port" == "$host_port" ]]; then
    if [[ "$url" == https://* ]]; then
      echo 443
    else
      echo 80
    fi
    return
  fi

  echo "$port"
}

PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
LOG_DIR="$ROOT_DIR/logs"
PID_DIR="$ROOT_DIR/.pids"
RAG_URL="${RAG_URL:-http://127.0.0.1:7100}"
RAG_PORT="${RAG_PORT:-$(url_port "$RAG_URL")}"
LB_URL="${LB_URL:-http://127.0.0.1:8000}"
QDRANT_PATH="${QDRANT_PATH:-$ROOT_DIR/qdrant_data}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:1b}"
OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-5m}"

mkdir -p "$LOG_DIR" "$PID_DIR"

if [[ ! -x "$PYTHON" ]]; then
  echo "Python not found at $PYTHON. Activate/install .venv first." >&2
  exit 1
fi

is_running() {
  local pid_file="$1"

  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" >/dev/null 2>&1
}

start_service() {
  local name="$1"
  shift
  local pid_file="$PID_DIR/$name.pid"
  local log_file="$LOG_DIR/$name.log"

  if is_running "$pid_file"; then
    echo "$name already running with PID $(cat "$pid_file")"
    return
  fi

  echo "Starting $name -> $log_file"
  (
    cd "$ROOT_DIR"
    exec nohup "$@"
  ) >"$log_file" 2>&1 &

  echo "$!" > "$pid_file"
}

wait_for_pid_exit() {
  local pid="$1"
  local attempts="${2:-20}"

  for _ in $(seq 1 "$attempts"); do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.1
  done

  return 1
}

terminate_pid() {
  local pid="$1"
  local label="$2"

  if ! kill -0 "$pid" >/dev/null 2>&1; then
    return
  fi

  echo "Stopping $label (PID $pid)"
  kill "$pid" >/dev/null 2>&1 || true

  if ! wait_for_pid_exit "$pid"; then
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi
}

stop_service() {
  local name="$1"
  local pid_file="$PID_DIR/$name.pid"

  if ! is_running "$pid_file"; then
    rm -f "$pid_file"
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  terminate_pid "$pid" "$name"

  rm -f "$pid_file"
}

stop_port_listener() {
  local port="$1"
  local pids

  if ! command -v lsof >/dev/null 2>&1; then
    return
  fi

  pids="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"

  for pid in $pids; do
    local command
    command="$(ps -p "$pid" -o command= 2>/dev/null || true)"

    case "$command" in
      *"-m lb.load_balancer"*|*"-m master.scheduler"*|*"-m workers.gpu_worker"*|*"-m rag.api"*)
        terminate_pid "$pid" "stale project service on port $port"
        ;;
      *)
        echo "Leaving non-project listener on port $port alone (PID $pid: ${command:-unknown})"
        ;;
    esac
  done
}

stop_matching_processes() {
  local label="$1"
  local pattern="$2"
  local pids

  if ! command -v pgrep >/dev/null 2>&1; then
    return
  fi

  pids="$(pgrep -f "$pattern" 2>/dev/null || true)"

  for pid in $pids; do
    if [[ "$pid" == "$$" || "$pid" == "${BASHPID:-}" ]]; then
      continue
    fi
    terminate_pid "$pid" "$label"
  done
}

stop_stale_project_services() {
  stop_matching_processes "stale load balancer" "[Pp]ython.*-m lb\\.load_balancer"
  stop_matching_processes "stale master service" "[Pp]ython.*-m master\\.scheduler"
  stop_matching_processes "stale worker service" "[Pp]ython.*-m workers\\.gpu_worker"
  stop_matching_processes "stale RAG service" "[Pp]ython.*-m rag\\.api"
}

wait_for_http() {
  local url="$1"
  local name="$2"
  local attempts="${3:-60}"

  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name is ready at $url"
      return
    fi
    sleep 0.5
  done

  echo "$name did not become ready at $url" >&2
  exit 1
}

set_strategy() {
  local strategy="$1"
  curl -fsS -X POST "$LB_URL/strategy/$strategy"
  echo
}

show_logs_hint() {
  echo
  echo "Logs are in: $LOG_DIR"
  echo "PIDs are in: $PID_DIR"
}

start_ollama_service() {
  if ! command -v ollama >/dev/null 2>&1; then
    echo "Ollama is not installed or not on PATH." >&2
    exit 1
  fi

  if curl -fsS "http://127.0.0.1:11434" >/dev/null 2>&1; then
    return
  fi

  if command -v brew >/dev/null 2>&1; then
    echo "Starting Ollama background service"
    brew services start ollama >/dev/null 2>&1 || true
    wait_for_http "http://127.0.0.1:11434" "Ollama service"
  else
    echo "Ollama service is not reachable. Start it manually with: ollama serve" >&2
    exit 1
  fi
}

unload_ollama_model() {
  if ! command -v ollama >/dev/null 2>&1; then
    return
  fi

  echo "Unloading Ollama model: $OLLAMA_MODEL"
  ollama stop "$OLLAMA_MODEL" >/dev/null 2>&1 || true
}

stop_ollama_service() {
  unload_ollama_model

  if command -v brew >/dev/null 2>&1; then
    echo "Stopping Ollama background service"
    brew services stop ollama >/dev/null 2>&1 || true
  else
    echo "Homebrew not found; stop Ollama manually if it is running."
  fi
}
