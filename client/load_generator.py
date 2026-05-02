import time
import threading
import argparse
from collections import Counter
import requests

LB_URL = "http://127.0.0.1:8000/query"
REQUEST_TIMEOUT = 120


def format_result_preview(result, max_length):
    one_line_result = " ".join(result.split())

    if len(one_line_result) <= max_length:
        return one_line_result

    return one_line_result[:max_length] + "..."


def send_request(
    request_id,
    results,
    lock,
    query,
    timeout,
    show_results,
    result_chars,
    max_tokens
):
    payload = {
        "id": request_id,
        "query": f"{query} Request {request_id}"
    }

    if max_tokens:
        payload["max_tokens"] = max_tokens

    start_time = time.time()

    try:
        response = requests.post(LB_URL, json=payload, timeout=timeout)
        total_latency = time.time() - start_time

        data = response.json()

        if data.get("success"):
            print(
                f"[Client] Request {request_id} | "
                f"Master {data['master_id']} | "
                f"Worker {data['worker_id']} | "
                f"Total Latency: {total_latency:.3f}s"
            )
            if show_results:
                print(
                    f"[LLM Answer {request_id}] "
                    f"{format_result_preview(data['result'], result_chars)}"
                )

            with lock:
                results["latencies"].append(total_latency)
                results["masters"].append(data["master_id"])
                results["workers"].append(data["worker_id"])
        else:
            print(f"[Client] Request {request_id} failed: {data.get('result')}")
            with lock:
                results["failures"] += 1

    except requests.exceptions.RequestException as error:
        print(f"[Client] Request {request_id} failed: {error}")
        with lock:
            results["failures"] += 1


def run_load_test(
    num_users=100,
    query="What is distributed computing?",
    timeout=REQUEST_TIMEOUT,
    show_results=False,
    result_chars=220,
    max_tokens=None
):
    threads = []
    lock = threading.Lock()
    results = {
        "latencies": [],
        "masters": [],
        "workers": [],
        "failures": 0
    }

    start_time = time.time()

    for i in range(num_users):
        thread = threading.Thread(
            target=send_request,
            args=(
                i,
                results,
                lock,
                query,
                timeout,
                show_results,
                result_chars,
                max_tokens
            )
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    total_time = time.time() - start_time

    print("\n========== TEST RESULTS ==========")
    print(f"Total users: {num_users}")
    print(f"Successful requests: {len(results['latencies'])}")
    print(f"Failed requests: {results['failures']}")
    print(f"Total time: {total_time:.3f}s")

    if results["latencies"]:
        latencies = results["latencies"]
        print(f"Average latency: {sum(latencies) / len(latencies):.3f}s")
        print(f"Min latency: {min(latencies):.3f}s")
        print(f"Max latency: {max(latencies):.3f}s")
        print(f"Throughput: {len(latencies) / total_time:.2f} requests/second")
        print(f"Master distribution: {dict(Counter(results['masters']))}")
        print(f"Worker distribution: {dict(Counter(results['workers']))}")

    print("==================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=REQUEST_TIMEOUT)
    parser.add_argument(
        "--query",
        default="What is distributed computing?"
    )
    parser.add_argument(
        "--show-results",
        action="store_true",
        help="Print a short preview of each LLM response."
    )
    parser.add_argument(
        "--result-chars",
        type=int,
        default=220,
        help="Maximum number of characters to print for each LLM response."
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="Request a larger Ollama generation only for this load test."
    )
    args = parser.parse_args()

    run_load_test(
        num_users=args.users,
        query=args.query,
        timeout=args.timeout,
        show_results=args.show_results,
        result_chars=args.result_chars,
        max_tokens=args.max_tokens
    )
