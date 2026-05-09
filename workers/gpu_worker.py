import os
import time
import argparse
import threading

from fastapi import FastAPI
import uvicorn

from common.models import RequestModel
from rag.retriever import retrieve_context
from llm.inference import OLLAMA_MODEL, run_llm

app = FastAPI()

SERVICE_HOST = os.getenv("SERVICE_HOST", "127.0.0.1")
WORKER_ID = 0
MASTER_ID = 0
active_tasks = 0
total_requests = 0
metrics_lock = threading.Lock()
GPU_CAPACITY = max(1, int(os.getenv("WORKER_GPU_CAPACITY", "2")))
failure_lock = threading.Lock()
fail_next_request = False
fail_next_delay = 0.0
fail_next_reason = "Simulated worker failure"


def consume_fail_next_request():
    global fail_next_request

    with failure_lock:
        should_fail = fail_next_request
        delay = fail_next_delay
        reason = fail_next_reason
        fail_next_request = False

    return should_fail, delay, reason


def calculate_gpu_utilization(task_count):
    return round(min(100.0, (task_count / GPU_CAPACITY) * 100.0), 2)


def begin_task():
    global active_tasks, total_requests

    with metrics_lock:
        active_tasks += 1
        total_requests += 1
        return calculate_gpu_utilization(active_tasks)


def end_task():
    global active_tasks

    with metrics_lock:
        active_tasks = max(0, active_tasks - 1)


def current_metrics():
    with metrics_lock:
        return {
            "active_tasks": active_tasks,
            "total_requests": total_requests,
            "gpu_capacity": GPU_CAPACITY,
            "gpu_utilization_percent": calculate_gpu_utilization(active_tasks)
        }


@app.post("/process")
def process_request(request: RequestModel):
    request_gpu_utilization = begin_task()

    start_time = time.time()

    print(f"[Worker {WORKER_ID}] Processing request {request.id}")

    try:
        should_fail, delay, reason = consume_fail_next_request()

        if should_fail:
            if delay > 0:
                time.sleep(delay)

            raise RuntimeError(reason)

        context = retrieve_context(request.query)
        result = run_llm(request.query, context, max_tokens=request.max_tokens)

        latency = time.time() - start_time

        return {
            "id": request.id,
            "result": result,
            "worker_id": WORKER_ID,
            "master_id": MASTER_ID,
            "latency": latency,
            "gpu_utilization_percent": request_gpu_utilization,
            "gpu_utilization_source": "simulated_worker_active_tasks",
            "gpu_capacity": GPU_CAPACITY,
            "llm_model": OLLAMA_MODEL,
            "success": True
        }
    except Exception as error:
        latency = time.time() - start_time

        return {
            "id": request.id,
            "result": f"Worker {WORKER_ID} failed during processing: {error}",
            "worker_id": WORKER_ID,
            "master_id": MASTER_ID,
            "latency": latency,
            "gpu_utilization_percent": request_gpu_utilization,
            "gpu_utilization_source": "simulated_worker_active_tasks",
            "gpu_capacity": GPU_CAPACITY,
            "llm_model": OLLAMA_MODEL,
            "success": False
        }
    finally:
        end_task()


@app.post("/simulate/fail-next")
def simulate_fail_next(delay: float = 1.0, reason: str = "Simulated worker failure"):
    global fail_next_request, fail_next_delay, fail_next_reason

    with failure_lock:
        fail_next_request = True
        fail_next_delay = delay
        fail_next_reason = reason

    return {
        "success": True,
        "worker_id": WORKER_ID,
        "message": "Next request will fail during processing",
        "delay": fail_next_delay,
        "reason": fail_next_reason
    }


@app.get("/health")
def health_check():
    metrics = current_metrics()

    return {
        "status": "alive",
        "worker_id": WORKER_ID,
        "master_id": MASTER_ID,
        "llm_model": OLLAMA_MODEL,
        "gpu_utilization_source": "simulated_worker_active_tasks",
        **metrics
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--master-id", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)

    args = parser.parse_args()

    WORKER_ID = args.id
    MASTER_ID = args.master_id

    uvicorn.run(app, host=SERVICE_HOST, port=args.port)
