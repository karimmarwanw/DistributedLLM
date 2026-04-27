print("""
Run each service in a separate terminal.

Workers:

1) Worker 0 under Master 0:
python -m workers.gpu_worker --id 0 --master-id 0 --port 9001

2) Worker 1 under Master 0:
python -m workers.gpu_worker --id 1 --master-id 0 --port 9002

3) Worker 2 under Master 1:
python -m workers.gpu_worker --id 2 --master-id 1 --port 9003

4) Worker 3 under Master 1:
python -m workers.gpu_worker --id 3 --master-id 1 --port 9004


Masters:

5) Master 0:
python -m master.scheduler --master-id 0 --port 8001 --workers 0:9001 1:9002

6) Master 1:
python -m master.scheduler --master-id 1 --port 8002 --workers 2:9003 3:9004


Load Balancer:

7) Load Balancer:
python -m lb.load_balancer


Client:

8) Client:
python -m client.load_generator
""")