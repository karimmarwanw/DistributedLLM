# Distributed LLM Inference System

This project simulates a distributed Large Language Model (LLM) inference service. It models how incoming user requests can be routed through a load balancer, scheduled by master nodes, processed by worker nodes, and optionally enriched with Retrieval-Augmented Generation (RAG) context before inference.

The system is built with Python, FastAPI, asynchronous HTTP-style service communication, local Ollama inference, and a local Qdrant-backed vector database.

## Features

- Client load generator for concurrent request testing
- Load balancer with multiple routing strategies:
  - Round Robin
  - Least Connections
  - Load-Aware routing
- Two master nodes, each managing its own worker pool
- Four worker nodes that simulate GPU inference workers
- Round Robin task scheduling from each master to its workers
- Local Ollama integration for real LLM inference without external APIs
- RAG pipeline using Qdrant local storage
- PDF/text document ingestion into the vector database
- Fault tolerance for worker failure and master failure scenarios
- Scripts for normal demos, load tests, RAG tests, and failover tests
- Single-Mac mode and two-MacBook distributed mode
- Metrics printed by the client:
  - success/failure count
  - latency
  - throughput
  - simulated GPU utilization
  - master distribution
  - worker distribution

## Architecture

```text
Client Load Generator
        |
        v
Load Balancer :8000
        |
        +------------------+
        |                  |
        v                  v
Master 0 :8001       Master 1 :8002
        |                  |
   +----+----+        +----+----+
   |         |        |         |
Worker 0  Worker 1  Worker 2  Worker 3
:9001     :9002     :9003     :9004
   |         |        |         |
   +---------+--------+---------+
             |
             v
      RAG Service :7100
             |
             v
      Qdrant Local VectorDB

Workers call Ollama locally for real LLM generation when Ollama mode is enabled.
```

## Repository Layout

```text
client/              Concurrent request generator
common/              Shared request/response models
lb/                  Load balancer service
master/              Master node scheduler
workers/             Worker node inference services
llm/                 Ollama inference wrapper
rag/                 RAG API, vector store, and ingestion logic
scripts/             Start, stop, test, RAG, and fault-tolerance scripts
requirements.txt     Python dependencies
```

Runtime folders such as `.venv/`, `logs/`, `.pids/`, and `qdrant_data/` are ignored by Git.

## Requirements

- Python 3.10+
- macOS, Linux, or Windows with Python support
- Ollama for local LLM inference
- `pdftotext` for PDF ingestion

On macOS:

```bash
brew install ollama
brew install poppler
```

Pull a small local model:

```bash
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

## Running the System

### Option 1: Simulation Mode

Simulation mode is best for high-concurrency tests because workers return simulated LLM responses instead of calling Ollama.

```bash
./scripts/start_simulation_system.sh
```

Run a 1000-request load test:

```bash
./scripts/test_load_simulation.sh 1000
```

### Option 2: Ollama Mode

Ollama mode uses a real local model for generation.

```bash
./scripts/start_ollama_system.sh
```

Run one RAG + Ollama request:

```bash
./scripts/test_ollama_rag_single.sh "why are threads useful in distributed systems?"
```

Run 10 concurrent Ollama requests:

```bash
./scripts/test_ollama_10.sh "why are threads useful in distributed systems?"
```

Stop the project services:

```bash
./scripts/stop_system.sh
```

Stop the project services and the Ollama background daemon:

```bash
./scripts/stop_system.sh --stop-ollama-service
```

### Option 3: Two-MacBook Distributed Mode

This mode runs the load balancer on Karim's MacBook and one master node on each MacBook.

```text
Karim MacBook: karims-macbook-pro.local
- Load balancer
- Master 0
- Worker 0
- Worker 1
- Local RAG service
- Local Ollama model: llama3.2:1b

Adam MacBook: Adams-MacBook-Pro.local
- Master 1
- Worker 2
- Worker 3
- Local RAG service
- Local Ollama model: phi:2.7b
```

Both MacBooks need this repository, the Python dependencies, Ollama, and the relevant model installed. They must be on the same network or hotspot. If macOS asks whether Python can accept incoming connections, allow it.

You can quickly test hostname resolution with:

```bash
ping karims-macbook-pro.local
ping Adams-MacBook-Pro.local
```

Start Adam's node first on Adam's MacBook:

```bash
./scripts/start_adam_distributed.sh
```

Then start Karim's coordinator on Karim's MacBook:

```bash
./scripts/start_karim_distributed.sh
```

Check that both machines can reach each other:

```bash
./scripts/check_distributed_network.sh
```

Run a distributed 10-request test from Karim's MacBook:

```bash
./scripts/test_distributed_10.sh "why are threads useful in distributed systems?"
```

Other distributed test scripts:

```bash
./scripts/test_distributed_single.sh "what is process context?"
./scripts/test_distributed_distribution_10.sh
./scripts/test_distributed_load.sh 10
./scripts/test_distributed_strategies.sh 10
./scripts/test_distributed_rag_retrieval.sh "what is process context?"
./scripts/test_distributed_worker_failover_karim.sh
./scripts/test_distributed_worker_failover_adam.sh
./scripts/test_distributed_master_down_failover.sh
./scripts/test_distributed_master_crash_during_processing.sh
./scripts/test_distributed_single_worker_master_failover.sh
```

Stop services on each MacBook:

```bash
./scripts/stop_adam_distributed.sh
./scripts/stop_karim_distributed.sh
```

If the `.local` hostnames are different on your network, override them:

```bash
KARIM_HOST=karims-macbook-pro.local ADAM_HOST=Adams-MacBook-Pro.local ./scripts/start_karim_distributed.sh
```

## RAG Document Ingestion

Start either the simulation system or Ollama system first, because the RAG service must be running.

Inject a PDF:

```bash
./scripts/inject_pdf.sh "/Users/yourname/Downloads/3-Processes.pdf"
```

Inject plain text:

```bash
./scripts/inject_text.sh notes "Distributed systems use multiple nodes to coordinate work."
```

Test retrieval directly:

```bash
./scripts/test_rag_retrieval.sh "what is process context?"
```

Documents are persisted in `qdrant_data/`, so they remain available after restarting the services.

In two-MacBook mode, each MacBook has its own RAG service and its own `qdrant_data/` folder. If you want both masters to answer from the same PDF, inject the PDF on both MacBooks.

## Load Balancing Strategies

The load balancer supports three strategies:

```bash
curl -X POST http://127.0.0.1:8000/strategy/round_robin
curl -X POST http://127.0.0.1:8000/strategy/least_connections
curl -X POST http://127.0.0.1:8000/strategy/load_aware
```

Round Robin rotates evenly between alive master nodes. Least Connections selects the master with the fewest active tasks. Load-Aware routing considers active tasks plus request history.

The load balancer also tracks requests that it has already assigned but that have not completed yet. This `in_flight` accounting is important during concurrent tests because health checks alone can be slightly stale. Least Connections uses `active_tasks + in_flight`; Load-Aware uses that same live load plus request history.

## Fault Tolerance Tests

Distributed two-MacBook fault tests:

```bash
./scripts/test_distributed_worker_failover_karim.sh
./scripts/test_distributed_worker_failover_adam.sh
./scripts/test_distributed_master_down_failover.sh
./scripts/test_distributed_single_worker_master_failover.sh
./scripts/test_distributed_master_crash_during_processing.sh
```

Local single-Mac fault tests:

Worker failure with retry to another worker:

```bash
./scripts/test_worker_failover_ollama.sh
./scripts/test_worker_failover_simulation.sh
```

Master 0 down before the request, then retry through Master 1:

```bash
./scripts/test_master_down_failover_ollama.sh
```

Only worker under Master 0 fails, Master 0 stays alive, then load balancer retries Master 1:

```bash
./scripts/test_single_worker_master_failover_ollama.sh
```

Master 0 crashes while a worker is processing, then load balancer retries Master 1:

```bash
./scripts/test_master_crash_during_processing_ollama.sh
```

## Useful Client Commands

Manual 10-user request test:

```bash
python -m client.load_generator \
  --users 10 \
  --timeout 400 \
  --query "why are threads useful in distributed systems?" \
  --show-results \
  --max-tokens 300
```

Full answer for a single request:

```bash
python -m client.load_generator \
  --users 1 \
  --timeout 400 \
  --query "what is process context?" \
  --full-answer \
  --max-tokens 900
```

## Environment Variables

Common variables:

```text
USE_OLLAMA=true|false
OLLAMA_MODEL=llama3.2:1b
OLLAMA_URL=http://127.0.0.1:11434/api/generate
OLLAMA_TIMEOUT=300
OLLAMA_NUM_PREDICT=300
OLLAMA_KEEP_ALIVE=5m
RAG_URL=http://127.0.0.1:7100
RAG_PORT=7100
QDRANT_PATH=./qdrant_data
LB_MASTER_TIMEOUT=300
WORKER_REQUEST_TIMEOUT=300
WORKER_GPU_CAPACITY=2
SERVICE_HOST=127.0.0.1
MASTER_URLS=0:http://127.0.0.1:8001,1:http://127.0.0.1:8002
WORKER_HOST=127.0.0.1
LB_QUERY_URL=http://127.0.0.1:8000/query
KARIM_HOST=karims-macbook-pro.local
ADAM_HOST=Adams-MacBook-Pro.local
KARIM_RAG_URL=http://karims-macbook-pro.local:7100
ADAM_RAG_URL=http://Adams-MacBook-Pro.local:7100
KARIM_MODEL=llama3.2:1b
ADAM_MODEL=phi:2.7b
```

Example with a different Ollama model:

```bash
OLLAMA_MODEL=qwen2.5:3b ./scripts/start_ollama_system.sh
```

Two-MacBook mode intentionally uses different local models:

```text
Karim: llama3.2:1b
Adam: phi:2.7b
```

The client output includes model distribution so you can see which model served each request.

## Notes on GPU Computing

The worker services are named GPU workers because they represent GPU inference nodes in the distributed architecture. In the current implementation, direct CUDA, NVIDIA GPU libraries, and Apple Metal code are not implemented inside this repository.

When Ollama mode is enabled, model execution is handled by Ollama locally. On supported MacBooks, Ollama may use Apple acceleration internally, but the project itself treats workers as distributed inference services rather than directly controlling GPU kernels.

The `GPU utilization` value printed by the client is a simulated worker utilization metric based on each worker's active tasks and configured `WORKER_GPU_CAPACITY`. It is included so every inference test reports the required performance metrics: latency, throughput, and GPU utilization.

## Current Limitations

- Distributed execution is simulated on one machine using multiple local FastAPI services.
- Worker nodes represent GPU workers, but no direct CUDA/NVIDIA/Metal programming is implemented.
- GPU utilization is simulated from worker load rather than read from real GPU hardware counters.
- Local Ollama inference is much slower than simulation mode for large load tests.
- Local Qdrant storage is suitable for this project demo; a production system would normally use a standalone Qdrant server.
- Fault tolerance retries requests, but it does not implement persistent queues or exactly-once execution.

## Project Status

Implemented:

- Load balancer and master-worker service architecture
- Round Robin, Least Connections, and Load-Aware master selection
- Round Robin worker scheduling
- Local Ollama inference
- RAG with document ingestion and persistent Qdrant storage
- Client-side load testing and metrics
- Worker and master failover scenarios

Possible future work:

- Real multi-machine deployment
- Hardware-level GPU metrics
- Standalone Qdrant server deployment
- Request queueing and durable retries
- More advanced scheduler policies
- Authentication and rate limiting
- Dashboard for live metrics
