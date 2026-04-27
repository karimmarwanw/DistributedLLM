import time
import threading
import requests

LB_URL = "http://127.0.0.1:8000/query"


def send_request(request_id, results):
    payload = {
        "id": request_id,
        "query": f"What is distributed computing? Request {request_id}"
    }

    start_time = time.time()

    try:
        response = requests.post(LB_URL, json=payload, timeout=20)
        total_latency = time.time() - start_time

        data = response.json()

        if data.get("success"):
            print(
                f"[Client] Request {request_id} | "
                f"Master {data['master_id']} | "
                f"Worker {data['worker_id']} | "
                f"Total Latency: {total_latency:.3f}s"
            )
            results.append(total_latency)
        else:
            print(f"[Client] Request {request_id} failed: {data.get('result')}")

    except requests.exceptions.RequestException as error:
        print(f"[Client] Request {request_id} failed: {error}")


def run_load_test(num_users=100):
    threads = []
    results = []

    start_time = time.time()

    for i in range(num_users):
        thread = threading.Thread(
            target=send_request,
            args=(i, results)
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    total_time = time.time() - start_time

    print("\n========== TEST RESULTS ==========")
    print(f"Total users: {num_users}")
    print(f"Successful requests: {len(results)}")
    print(f"Failed requests: {num_users - len(results)}")
    print(f"Total time: {total_time:.3f}s")

    if results:
        print(f"Average latency: {sum(results) / len(results):.3f}s")
        print(f"Throughput: {len(results) / total_time:.2f} requests/second")

    print("==================================")


if __name__ == "__main__":
    run_load_test(num_users=200)