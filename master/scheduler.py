class Scheduler:
    def __init__(self, workers):
        self.workers = workers
        self.index = 0
        self.completed_requests = 0
        self.failed_requests = 0

    def get_next_worker_round_robin(self):
        alive_workers = [worker for worker in self.workers if worker.is_alive]

        if not alive_workers:
            raise Exception("No alive workers available")

        worker = alive_workers[self.index % len(alive_workers)]
        self.index += 1

        return worker

    def handle_request(self, request):
        print(f"[Scheduler] Scheduling request {request.id}")

        try:
            worker = self.get_next_worker_round_robin()
            response = worker.process(request)

            self.completed_requests += 1
            return response

        except Exception as error:
            print(f"[Scheduler] Request {request.id} failed: {error}")

            self.failed_requests += 1
            return None