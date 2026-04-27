import argparse
import requests
from fastapi import FastAPI
import uvicorn

from common.models import RequestModel

app = FastAPI()

MASTER_ID = 0
workers = []
current_worker_index = 0
active_tasks = 0
total_requests = 0


def get_alive_workers():
    alive_workers = []

    for worker in workers:
        try:
            response = requests.get(worker["url"] + "/health", timeout=1)

            if response.status_code == 200:
                data = response.json()
                worker["alive"] = True
                worker["active_tasks"] = data.get("active_tasks", 0)
                worker["total_requests"] = data.get("total_requests", 0)
                alive_workers.append(worker)
            else:
                worker["alive"] = False

        except requests.exceptions.RequestException:
            worker["alive"] = False

    return alive_workers


def choose_worker_round_robin():
    global current_worker_index

    alive_workers = get_alive_workers()

    if not alive_workers:
        return None

    selected_worker = alive_workers[current_worker_index % len(alive_workers)]
    current_worker_index += 1

    return selected_worker


@app.post("/schedule")
def schedule_request(request: RequestModel):
    global active_tasks, total_requests

    active_tasks += 1
    total_requests += 1

    print(f"[Master {MASTER_ID}] Received request {request.id}")

    worker = choose_worker_round_robin()

    if worker is None:
        active_tasks -= 1
        return {
            "id": request.id,
            "success": False,
            "result": "No alive workers available",
            "master_id": MASTER_ID
        }

    try:
        print(
            f"[Master {MASTER_ID}] Sending request {request.id} "
            f"to Worker {worker['id']}"
        )

        response = requests.post(
            worker["url"] + "/process",
            json=request.model_dump(),
            timeout=10
        )

        active_tasks -= 1
        return response.json()

    except requests.exceptions.RequestException:
        active_tasks -= 1

        return {
            "id": request.id,
            "success": False,
            "result": f"Worker {worker['id']} failed",
            "master_id": MASTER_ID
        }


@app.get("/health")
def health_check():
    return {
        "status": "alive",
        "master_id": MASTER_ID,
        "active_tasks": active_tasks,
        "total_requests": total_requests,
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