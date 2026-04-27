from workers.gpu_worker import GPUWorker
from lb.load_balancer import LoadBalancer
from master.scheduler import Scheduler
from client.load_generator import run_load_test


def main():
    workers = [
        GPUWorker(worker_id=0),
        GPUWorker(worker_id=1),
        GPUWorker(worker_id=2),
        GPUWorker(worker_id=3)
    ]

    scheduler = Scheduler(workers)

    load_balancer = LoadBalancer()
    load_balancer.attach_scheduler(scheduler)

    run_load_test(load_balancer, num_users=100)


if __name__ == "__main__":
    main()