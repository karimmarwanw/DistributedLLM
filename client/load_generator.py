import threading
import time

from common.models import Request


def simulate_user(lb, user_id, results):
    request = Request(
        id=user_id,
        query=f"What is distributed computing? User {user_id}"
    )

    response = lb.handle_request(request)

    if response:
        print(
            f"[Client] Request {response.id} | "
            f"Worker {response.worker_id} | "
            f"Latency: {response.latency:.3f}s"
        )
        results.append(response)
    else:
        print(f"[Client] Request {user_id} failed")


def run_load_test(lb, num_users=100):
    threads = []
    results = []

    start_time = time.time()

    for i in range(num_users):
        thread = threading.Thread(
            target=simulate_user,
            args=(lb, i, results)
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
        avg_latency = sum(response.latency for response in results) / len(results)
        throughput = len(results) / total_time

        print(f"Average latency: {avg_latency:.3f}s")
        print(f"Throughput: {throughput:.2f} requests/second")

    print("==================================")