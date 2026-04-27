import time
import random

from common.models import Request, Response
from rag.retriever import retrieve_context
from llm.inference import run_llm


class GPUWorker:
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.active_tasks = 0
        self.is_alive = True

    def process(self, request: Request) -> Response:
        if not self.is_alive:
            raise Exception(f"Worker {self.worker_id} is down")

        self.active_tasks += 1
        start_time = time.time()

        try:
            print(f"[Worker {self.worker_id}] Processing request {request.id}")

            # rag step
            context = retrieve_context(request.query)

            # llm step
            result = run_llm(request.query, context)

            latency = time.time() - start_time

            return Response(
                id=request.id,
                result=result,
                latency=latency,
                worker_id=self.worker_id,
                success=True
            )

        finally:
            self.active_tasks -= 1

    def fail(self):
        self.is_alive = False
        print(f"[Worker {self.worker_id}] FAILED")

    def recover(self):
        self.is_alive = True
        print(f"[Worker {self.worker_id}] RECOVERED")