import argparse
import os
import threading

import requests
from fastapi import FastAPI
import uvicorn

from common.gpu_metrics import get_gpu_metrics
from common.models import RequestModel

app = FastAPI()

SERVICE_HOST = os.getenv("SERVICE_HOST", "127.0.0.1")
WORKER_HOST = os.getenv("WORKER_HOST", "127.0.0.1")
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


def simulated_master_gpu_utilization(task_count):
    return round(min(100.0, (task_count / max(1, len(workers))) * 100.0), 2)


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
        current_active_tasks = active_tasks
        current_total_requests = total_requests

    gpu_metrics = get_gpu_metrics(
        fallback_percent=simulated_master_gpu_utilization(current_active_tasks),
        fallback_source="simulated_master_active_tasks"
    )

    return {
        "active_tasks": current_active_tasks,
        "total_requests": current_total_requests,
        "master_gpu_utilization_percent": gpu_metrics["gpu_utilization_percent"],
        "gpu_utilization_percent": gpu_metrics["gpu_utilization_percent"],
        "gpu_utilization_source": gpu_metrics["gpu_utilization_source"],
        "gpu_model": gpu_metrics["gpu_model"],
        "gpu_core_count": gpu_metrics["gpu_core_count"]
    }


def attach_master_gpu_metrics(response_data):
    metrics = current_metrics()
    worker_gpu_utilization = response_data.get("gpu_utilization_percent")

    response_data["worker_gpu_utilization_percent"] = worker_gpu_utilization
    response_data["master_gpu_utilization_percent"] = metrics[
        "master_gpu_utilization_percent"
    ]
    response_data["gpu_utilization_percent"] = metrics["gpu_utilization_percent"]
    response_data["gpu_utilization_source"] = metrics["gpu_utilization_source"]
    response_data["gpu_model"] = metrics["gpu_model"]
    response_data["gpu_core_count"] = metrics["gpu_core_count"]

    return response_data


def failed_schedule_response(request, result, attempted_workers):
    metrics = current_metrics()

    return {
        "id": request.id,
        "success": False,
        "result": result,
        "master_id": MASTER_ID,
        "attempted_workers": attempted_workers,
        "master_gpu_utilization_percent": metrics["master_gpu_utilization_percent"],
        "gpu_utilization_percent": metrics["gpu_utilization_percent"],
        "gpu_utilization_source": metrics["gpu_utilization_source"],
        "gpu_model": metrics["gpu_model"],
        "gpu_core_count": metrics["gpu_core_count"]
    }


def current_worker_summary():
    alive_workers = get_alive_workers()

    return {
        "workers": alive_workers,
        "worker_gpu_utilizations_percent": [
            worker.get("gpu_utilization_percent")
            for worker in alive_workers
        ]
    }


def master_health_payload():
    metrics = current_metrics()
    worker_summary = current_worker_summary()

    return {
        "status": "alive",
        "master_id": MASTER_ID,
        **metrics,
        **worker_summary
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


def parse_worker_spec(item):
    worker_id, worker_address = item.split(":", 1)

    if worker_address.startswith(("http://", "https://")):
        worker_url = worker_address.rstrip("/")
    else:
        worker_url = f"http://{WORKER_HOST}:{worker_address}"

    return {
        "id": int(worker_id),
        "url": worker_url,
        "alive": True,
        "active_tasks": 0,
        "total_requests": 0,
        "gpu_utilization_percent": 0,
        "gpu_capacity": None
    }


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
                return failed_schedule_response(
                    request,
                    last_error,
                    attempted_workers
                )

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
                    return attach_master_gpu_metrics(data)

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


@app.post("/simulate/reset-worker-round-robin")
def reset_worker_round_robin(index: int = 0):
    global current_worker_index

    with worker_index_lock:
        current_worker_index = max(0, index)

    return {
        "success": True,
        "master_id": MASTER_ID,
        "current_worker_index": current_worker_index
    }


@app.get("/health")
def health_check():
    return master_health_payload()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--master-id", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--workers", nargs="+", required=True)

    args = parser.parse_args()

    MASTER_ID = args.master_id

    workers = []

    for item in args.workers:
        workers.append(parse_worker_spec(item))

    uvicorn.run(app, host=SERVICE_HOST, port=args.port)
