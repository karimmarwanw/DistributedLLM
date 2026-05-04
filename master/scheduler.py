import argparse
import os
import threading

import requests
from fastapi import FastAPI
import uvicorn

from common.models import RequestModel

app = FastAPI()

MASTER_ID = 0
workers = []
current_worker_index = 0
worker_index_lock = threading.Lock()
active_tasks = 0
total_requests = 0
metrics_lock = threading.Lock()
WORKER_REQUEST_TIMEOUT = float(os.getenv("WORKER_REQUEST_TIMEOUT", "300"))
failure_lock = threading.Lock()
fail_during_next_schedule = False
fail_during_next_schedule_delay = 2.0
fail_during_next_schedule_reason = "Simulated master failure during scheduling"


def consume_fail_during_next_schedule():
    global fail_during_next_schedule

    with failure_lock:
        should_fail = fail_during_next_schedule
        delay = fail_during_next_schedule_delay
        reason = fail_during_next_schedule_reason
        fail_during_next_schedule = False

    return should_fail, delay, reason


def crash_master_after_delay(delay, reason):
    print(
        f"[Master {MASTER_ID}] {reason}. "
        f"Crashing master process in {delay:.1f}s."
    )
    timer = threading.Timer(delay, lambda: os._exit(1))
    timer.daemon = True
    timer.start()


def begin_task():
    global active_tasks, total_requests

    with metrics_lock:
        active_tasks += 1
        total_requests += 1


def end_task():
    global active_tasks

    with metrics_lock:
        active_tasks = max(0, active_tasks - 1)


def current_metrics():
    with metrics_lock:
        return {
            "active_tasks": active_tasks,
            "total_requests": total_requests
        }


def get_alive_workers(excluded_worker_ids=None):
    excluded_worker_ids = excluded_worker_ids or set()
    alive_workers = []

    for worker in workers:
        if worker["id"] in excluded_worker_ids:
            continue

        try:
            response = requests.get(worker["url"] + "/health", timeout=1)

            if response.status_code == 200:
                data = response.json()
                worker["alive"] = True
                worker["active_tasks"] = data.get("active_tasks", 0)
                worker["total_requests"] = data.get("total_requests", 0)
                worker["gpu_utilization_percent"] = data.get(
                    "gpu_utilization_percent", 0
                )
                worker["gpu_capacity"] = data.get("gpu_capacity")
                alive_workers.append(worker)
            else:
                worker["alive"] = False

        except requests.exceptions.RequestException:
            worker["alive"] = False

    return alive_workers


def choose_worker_round_robin(excluded_worker_ids=None):
    global current_worker_index

    alive_workers = get_alive_workers(excluded_worker_ids)

    if not alive_workers:
        return None

    with worker_index_lock:
        selected_worker = alive_workers[current_worker_index % len(alive_workers)]
        current_worker_index += 1

    return selected_worker


def mark_worker_failed(worker):
    worker["alive"] = False


@app.post("/schedule")
def schedule_request(request: RequestModel):
    begin_task()

    print(f"[Master {MASTER_ID}] Received request {request.id}")

    attempted_workers = []
    last_error = "No alive workers available"

    try:
        while True:
            worker = choose_worker_round_robin(set(attempted_workers))

            if worker is None:
                return {
                    "id": request.id,
                    "success": False,
                    "result": last_error,
                    "master_id": MASTER_ID,
                    "attempted_workers": attempted_workers
                }

            attempted_workers.append(worker["id"])

            try:
                print(
                    f"[Master {MASTER_ID}] Sending request {request.id} "
                    f"to Worker {worker['id']}"
                )

                should_fail, delay, reason = consume_fail_during_next_schedule()

                if should_fail:
                    crash_master_after_delay(delay, reason)

                response = requests.post(
                    worker["url"] + "/process",
                    json=request.model_dump(),
                    timeout=WORKER_REQUEST_TIMEOUT
                )
                response.raise_for_status()

                data = response.json()

                if data.get("success", False):
                    return data

                last_error = data.get("result", f"Worker {worker['id']} failed")
                mark_worker_failed(worker)
                print(
                    f"[Master {MASTER_ID}] Worker {worker['id']} failed for "
                    f"request {request.id}. Retrying another worker."
                )

            except requests.exceptions.RequestException as error:
                last_error = f"Worker {worker['id']} failed: {error}"
                mark_worker_failed(worker)
                print(
                    f"[Master {MASTER_ID}] Worker {worker['id']} failed for "
                    f"request {request.id}. Retrying another worker."
                )
    finally:
        end_task()


@app.post("/simulate/fail-during-next-schedule")
def simulate_fail_during_next_schedule(
    delay: float = 2.0,
    reason: str = "Simulated master failure during scheduling"
):
    global fail_during_next_schedule
    global fail_during_next_schedule_delay
    global fail_during_next_schedule_reason

    with failure_lock:
        fail_during_next_schedule = True
        fail_during_next_schedule_delay = delay
        fail_during_next_schedule_reason = reason

    return {
        "success": True,
        "master_id": MASTER_ID,
        "message": "Master will crash during the next scheduled request",
        "delay": fail_during_next_schedule_delay,
        "reason": fail_during_next_schedule_reason
    }


@app.get("/health")
def health_check():
    metrics = current_metrics()

    return {
        "status": "alive",
        "master_id": MASTER_ID,
        **metrics,
        "workers": get_alive_workers()
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--master-id", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--workers", nargs="+", required=True)

    args = parser.parse_args()

    MASTER_ID = args.master_id

    workers = []

    for item in args.workers:
        worker_id, worker_port = item.split(":")
        workers.append({
            "id": int(worker_id),
            "url": f"http://127.0.0.1:{worker_port}",
            "alive": True,
            "active_tasks": 0,
            "total_requests": 0
        })

    uvicorn.run(app, host="127.0.0.1", port=args.port)
