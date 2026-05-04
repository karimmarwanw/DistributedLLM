import os
import threading

import requests
from fastapi import FastAPI
import uvicorn

from common.models import RequestModel

app = FastAPI()

masters = [
    {
        "id": 0,
        "url": "http://127.0.0.1:8001",
        "alive": True,
        "active_tasks": 0,
        "total_requests": 0
    },
    {
        "id": 1,
        "url": "http://127.0.0.1:8002",
        "alive": True,
        "active_tasks": 0,
        "total_requests": 0
    }
]

current_master_index = 0
master_index_lock = threading.Lock()

LOAD_BALANCING_STRATEGY = "round_robin"
MASTER_REQUEST_TIMEOUT = float(os.getenv("LB_MASTER_TIMEOUT", "300"))
# Options:
# "round_robin"
# "least_connections"
# "load_aware"


def update_master_health(excluded_master_ids=None):
    excluded_master_ids = excluded_master_ids or set()
    alive_masters = []

    for master in masters:
        if master["id"] in excluded_master_ids:
            continue

        try:
            response = requests.get(master["url"] + "/health", timeout=1)

            if response.status_code == 200:
                data = response.json()
                master["alive"] = True
                master["active_tasks"] = data.get("active_tasks", 0)
                master["total_requests"] = data.get("total_requests", 0)
                alive_masters.append(master)
            else:
                master["alive"] = False

        except requests.exceptions.RequestException:
            master["alive"] = False

    return alive_masters


def choose_master_round_robin(alive_masters):
    global current_master_index

    with master_index_lock:
        selected_master = alive_masters[current_master_index % len(alive_masters)]
        current_master_index += 1

    return selected_master


def choose_master_least_connections(alive_masters):
    return min(alive_masters, key=lambda master: master["active_tasks"])


def choose_master_load_aware(alive_masters):
    return min(
        alive_masters,
        key=lambda master: master["active_tasks"] + (master["total_requests"] * 0.01)
    )


def choose_master(excluded_master_ids=None):
    alive_masters = update_master_health(excluded_master_ids)

    if not alive_masters:
        return None

    if LOAD_BALANCING_STRATEGY == "round_robin":
        return choose_master_round_robin(alive_masters)

    if LOAD_BALANCING_STRATEGY == "least_connections":
        return choose_master_least_connections(alive_masters)

    if LOAD_BALANCING_STRATEGY == "load_aware":
        return choose_master_load_aware(alive_masters)

    return choose_master_round_robin(alive_masters)


def mark_master_failed(master):
    master["alive"] = False


def should_retry_another_master(response_data):
    if response_data.get("success", False):
        return False

    result = response_data.get("result", "")
    retryable_messages = [
        "No alive workers available",
        "Worker "
    ]

    return any(message in result for message in retryable_messages)


@app.post("/query")
def handle_query(request: RequestModel):
    print(f"[Load Balancer] Received request {request.id}")

    attempted_masters = []
    last_error = "No alive master nodes available"

    while True:
        master = choose_master(set(attempted_masters))

        if master is None:
            return {
                "id": request.id,
                "success": False,
                "result": last_error,
                "attempted_masters": attempted_masters
            }

        attempted_masters.append(master["id"])

        try:
            print(
                f"[Load Balancer] Sending request {request.id} "
                f"to Master {master['id']}"
            )

            response = requests.post(
                master["url"] + "/schedule",
                json=request.model_dump(),
                timeout=MASTER_REQUEST_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()

            if should_retry_another_master(data):
                last_error = data.get("result", f"Master {master['id']} failed")
                print(
                    f"[Load Balancer] Master {master['id']} could not handle "
                    f"request {request.id}. Retrying another master."
                )
                continue

            return data

        except requests.exceptions.RequestException as error:
            last_error = f"Master {master['id']} failed: {error}"
            mark_master_failed(master)
            print(
                f"[Load Balancer] Master {master['id']} failed for request "
                f"{request.id}. Retrying another master."
            )


@app.get("/health")
def health_check():
    return {
        "status": "load balancer alive",
        "strategy": LOAD_BALANCING_STRATEGY,
        "masters": update_master_health()
    }


@app.post("/strategy/{strategy_name}")
def change_strategy(strategy_name: str):
    global LOAD_BALANCING_STRATEGY

    allowed = ["round_robin", "least_connections", "load_aware"]

    if strategy_name not in allowed:
        return {
            "success": False,
            "message": f"Invalid strategy. Use one of: {allowed}"
        }

    LOAD_BALANCING_STRATEGY = strategy_name

    return {
        "success": True,
        "strategy": LOAD_BALANCING_STRATEGY
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
