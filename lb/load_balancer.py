class LoadBalancer:
    def __init__(self):
        self.scheduler = None

    def attach_scheduler(self, scheduler):
        self.scheduler = scheduler

    def handle_request(self, request):
        print(f"[Load Balancer] Received request {request.id}")

        if self.scheduler is None:
            raise Exception("No scheduler attached to load balancer")

        return self.scheduler.handle_request(request)