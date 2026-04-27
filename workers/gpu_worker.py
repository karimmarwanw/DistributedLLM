import time
import argparse
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


@app.post("/process")
def process_request(request: RequestModel):
    global active_tasks, total_requests

    active_tasks += 1
    total_requests += 1

    start_time = time.time()

    print(f"[Worker {WORKER_ID}] Processing request {request.id}")

    context = retrieve_context(request.query)
    result = run_llm(request.query, context)

    latency = time.time() - start_time

    active_tasks -= 1

    return {
        "id": request.id,
        "result": result,
        "worker_id": WORKER_ID,
        "master_id": MASTER_ID,
        "latency": latency,
        "success": True
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