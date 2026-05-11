# Distributed LLM Inference System

A distributed Python system for handling high-concurrency Large Language Model (LLM) requests with load balancing, master-worker task scheduling, Retrieval-Augmented Generation (RAG), GPU-aware metrics, and fault-tolerance demos.

The project was built for the CSE354 Distributed Computing coursework: **Efficient Load Balancing and GPU Cluster Task Distribution for Handling 1000+ Concurrent LLM Requests**. It simulates a production-style AI serving cluster where many client requests are routed through a load balancer, scheduled by master controllers, processed by GPU worker nodes, optionally enriched with document context, and measured for latency, throughput, worker distribution, and GPU utilization.

## Highlights

- Concurrent client load generator for 1 to 1000+ simulated users
- FastAPI services for the load balancer, master nodes, worker nodes, and RAG API
- Three load-balancing strategies:
  - Round Robin
  - Least Connections
  - Load-Aware routing using active tasks, in-flight requests, history, and GPU metrics
- Two-master, four-worker cluster topology for local demos
- Two-MacBook distributed mode for physical multi-machine execution
- Worker-level task retry when a GPU worker fails
- Master-level retry when a master is unavailable or cannot complete a task
- Optional real LLM inference through Ollama
- Fast simulation mode for stress/load tests
- RAG document ingestion from text or PDF files
- Persistent local Qdrant vector database
- macOS GPU telemetry through `ioreg`, with simulated fallback metrics
- Scripted demos for load tests, RAG retrieval, routing strategies, worker failover, and master failover

## Architecture

```text
Client Load Generator
        |
        v
Load Balancer :8000
        |
        +---------------------+
        |                     |
        v                     v
Master 0 :8001          Master 1 :8002
        |                     |
   +----+----+           +----+----+
   |         |           |         |
Worker 0  Worker 1   Worker 2  Worker 3
:9001     :9002      :9003     :9004
   |         |           |         |
   +---------+-----------+---------+
             |
             v
      RAG Service :7100
             |
             v
      Qdrant Local Vector Store

Workers call Ollama locally when Ollama mode is enabled.
```

## Repository Layout

```text
client/              Concurrent request generator and benchmark output
common/              Shared Pydantic models and GPU metric helpers
lb/                  Load balancer service and routing strategies
master/              Master scheduler and worker failover logic
workers/             GPU worker API, RAG lookup, and LLM execution
llm/                 Ollama/simulation inference wrapper
rag/                 RAG API, ingestion, retrieval, and vector store code
scripts/             Start, stop, test, RAG, and fault-tolerance scripts
docs/                Project report and supporting documentation
requirements.txt     Python dependencies
main.py              Manual service startup guide
```

Runtime folders such as `.venv/`, `logs/`, `.pids/`, and `qdrant_data/` are intentionally not versioned.

## Requirements

- Python 3.10+
- `pip` and `venv`
- Ollama for real local LLM inference
- Poppler `pdftotext` for PDF ingestion
- macOS, Linux, or Windows for simulation mode
- macOS for the built-in real GPU telemetry path

On macOS:

```bash
brew install ollama
brew install poppler
ollama pull llama3.2:1b
```

## Setup

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
chmod +x scripts/*.sh
```

## Quick Start

Simulation mode is the best path for high-concurrency tests because workers return simulated LLM responses quickly.

```bash
./scripts/start_simulation_system.sh
./scripts/test_load_simulation.sh 1000
./scripts/stop_system.sh
```

Ollama mode uses a real local model:

```bash
./scripts/start_ollama_system.sh
./scripts/test_ollama_rag_single.sh "why are threads useful in distributed systems?"
./scripts/stop_system.sh
```

Stop Ollama as well:

```bash
./scripts/stop_system.sh --stop-ollama-service
```

## Running Load Tests

Run a custom client test:

```bash
python -m client.load_generator \
  --users 100 \
  --timeout 120 \
  --query "What is distributed computing?" \
  --show-results \
  --max-tokens 300
```

Print one full response:

```bash
python -m client.load_generator \
  --users 1 \
  --timeout 400 \
  --query "what is process context?" \
  --full-answer \
  --max-tokens 900
```

The client reports:

- successful and failed request counts
- total execution time
- throughput in requests per second
- average, minimum, and maximum latency
- master distribution
- worker distribution
- model distribution
- GPU utilization summary

## Load-Balancing Strategies

Change strategy while the load balancer is running:

```bash
curl -X POST http://127.0.0.1:8000/strategy/round_robin
curl -X POST http://127.0.0.1:8000/strategy/least_connections
curl -X POST http://127.0.0.1:8000/strategy/load_aware
```

Strategy behavior:

- `round_robin`: rotates evenly across alive master nodes.
- `least_connections`: chooses the master with the smallest `active_tasks + in_flight` count.
- `load_aware`: combines active load, in-flight load, request history, and GPU utilization.

Health and routing state:

```bash
curl http://127.0.0.1:8000/health
```

## RAG Document Ingestion

Start the system first so the RAG service is available, then ingest a PDF:

```bash
./scripts/inject_pdf.sh "/Users/yourname/Downloads/lecture.pdf"
```

Ingest text:

```bash
./scripts/inject_text.sh notes "Distributed systems coordinate work across multiple networked nodes."
```

Test retrieval:

```bash
./scripts/test_rag_retrieval.sh "what is process context?"
```

The RAG pipeline chunks text, embeds chunks with a deterministic hashed vector representation, stores them in Qdrant, and retrieves relevant context with vector search plus lexical keyword filtering. Data persists in `qdrant_data/`.

## Fault-Tolerance Tests

Local worker failover:

```bash
./scripts/test_worker_failover_simulation.sh
./scripts/test_worker_failover_ollama.sh
```

Local master failover:

```bash
./scripts/test_master_down_failover_ollama.sh
./scripts/test_single_worker_master_failover_ollama.sh
./scripts/test_master_crash_during_processing_ollama.sh
```

Distributed two-MacBook tests:

```bash
./scripts/test_distributed_worker_failover_karim.sh
./scripts/test_distributed_worker_failover_adam.sh
./scripts/test_distributed_master_down_failover.sh
./scripts/test_distributed_master_crash_during_processing.sh
./scripts/test_distributed_single_worker_master_failover.sh
```

## Two-MacBook Distributed Mode

Default physical deployment:

```text
Karim MacBook: karims-macbook-pro.local
- Load balancer
- Master 0
- Worker 0
- Worker 1
- RAG service
- Ollama model: llama3.2:1b

Adam MacBook: Adams-MacBook-Pro.local
- Master 1
- Worker 2
- Worker 3
- RAG service
- Ollama model: phi:2.7b
```

Start Adam first:

```bash
./scripts/start_adam_distributed.sh
```

Start Karim second:

```bash
./scripts/start_karim_distributed.sh
```

Check networking and run distributed tests:

```bash
./scripts/check_distributed_network.sh
./scripts/test_distributed_10.sh "why are threads useful in distributed systems?"
./scripts/test_distributed_load.sh 10
./scripts/test_distributed_strategies.sh 10
```

Stop both sides:

```bash
./scripts/stop_adam_distributed.sh
./scripts/stop_karim_distributed.sh
```

Override hostnames if needed:

```bash
KARIM_HOST=karims-macbook-pro.local ADAM_HOST=Adams-MacBook-Pro.local ./scripts/start_karim_distributed.sh
```

## Environment Variables

Common configuration:

```text
USE_OLLAMA=true|false
OLLAMA_MODEL=llama3.2:1b
OLLAMA_URL=http://127.0.0.1:11434/api/generate
OLLAMA_TIMEOUT=300
OLLAMA_NUM_PREDICT=300
OLLAMA_TEMPERATURE=0.2
OLLAMA_KEEP_ALIVE=5m
RAG_URL=http://127.0.0.1:7100
RAG_PORT=7100
QDRANT_PATH=./qdrant_data
QDRANT_URL=
RAG_TOP_K=3
LB_MASTER_TIMEOUT=300
WORKER_REQUEST_TIMEOUT=300
WORKER_GPU_CAPACITY=2
GPU_METRICS_MODE=auto
GPU_METRICS_CACHE_SECONDS=1.0
GPU_METRICS_COMMAND_TIMEOUT=0.75
LB_GPU_LOAD_WEIGHT=1.0
SERVICE_HOST=127.0.0.1
MASTER_URLS=0:http://127.0.0.1:8001,1:http://127.0.0.1:8002
WORKER_HOST=127.0.0.1
LB_QUERY_URL=http://127.0.0.1:8000/query
```

Example:

```bash
OLLAMA_MODEL=qwen2.5:3b ./scripts/start_ollama_system.sh
```

## Implemented Requirements

- Load balancing: implemented with Round Robin, Least Connections, and Load-Aware routing.
- GPU cluster task distribution: modeled with master schedulers and worker services.
- LLM inference: implemented with Ollama mode and simulation mode.
- RAG integration: implemented with document ingestion, retrieval, and prompt augmentation.
- Scalability: tested through thread-based client load generation up to 1000 requests in simulation mode.
- Fault tolerance: implemented through worker retries, master retries, health checks, and failure simulation endpoints.
- Monitoring: implemented through client metrics, service health endpoints, logs, and GPU utilization sampling.

## Limitations

- Worker services represent GPU inference nodes, but the project does not directly implement CUDA, NVIDIA, or Metal kernels.
- Single-machine mode simulates a distributed cluster using multiple local services.
- Ollama inference speed depends heavily on local hardware and model size.
- Local Qdrant storage is appropriate for demos; production deployments should use a standalone Qdrant service.
- Retry logic is request-level and does not provide durable queues or exactly-once processing.
- macOS real GPU telemetry is device-level, not per-worker-process utilization.

## Documentation

See [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md) for the full report-style explanation of the problem, design, implementation, testing approach, limitations, and future work.

See [docs/CODE_REVIEW.md](docs/CODE_REVIEW.md) for code-review notes, risks, and recommended improvements before final submission.

The submission-ready PDF report is available at [docs/DistributedLLM_Project_Report.pdf](docs/DistributedLLM_Project_Report.pdf).
