import time
import argparse
import threading

from fastapi import FastAPI
import uvicorn

from common.models import RequestModel
from rag.retriever import retrieve_context
from llm.inference import run_llm

app = FastAPI()

WORKER_ID = 0
MASTER_ID = 0
active_tasks = 0
total_requests = 0
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


@app.post("/process")
def process_request(request: RequestModel):
    global active_tasks, total_requests

    active_tasks += 1
    total_requests += 1

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
            "success": False
        }
    finally:
        active_tasks -= 1


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
    return {
        "status": "alive",
        "worker_id": WORKER_ID,
        "master_id": MASTER_ID,
        "active_tasks": active_tasks,
        "total_requests": total_requests
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--master-id", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)

    args = parser.parse_args()

    WORKER_ID = args.id
    MASTER_ID = args.master_id

    uvicorn.run(app, host="127.0.0.1", port=args.port)
