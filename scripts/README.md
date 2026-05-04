# Scenario Scripts

Run all scripts from the project root or directly by path.

## Start / Stop

```bash
./scripts/start_simulation_system.sh
./scripts/start_ollama_system.sh
./scripts/stop_system.sh
./scripts/stop_system.sh --stop-ollama-service
```

## RAG

```bash
./scripts/inject_pdf.sh "/Users/karimmarwan/Downloads/3-Processes.pdf"
./scripts/inject_text.sh notes "Distributed systems use multiple nodes."
./scripts/test_rag_retrieval.sh "what is process context?"
```

## Normal Tests

```bash
./scripts/test_ollama_rag_single.sh "why are threads useful in distributed systems?"
./scripts/test_ollama_10.sh "why are threads useful in distributed systems?"
./scripts/test_distribution_10.sh
./scripts/test_load_simulation.sh 1000
./scripts/test_strategies.sh 100
```

Inference test output includes latency, throughput, simulated GPU utilization, master distribution, and worker distribution.

## Fault Tolerance

Worker fails while processing, then Master 0 retries Worker 1:

```bash
./scripts/test_worker_failover_ollama.sh
./scripts/test_worker_failover_simulation.sh
```

Master 0 is down before request, then load balancer routes to Master 1:

```bash
./scripts/test_master_down_failover_ollama.sh
```

The only worker under Master 0 fails, Master 0 stays alive, then load balancer retries Master 1:

```bash
./scripts/test_single_worker_master_failover_ollama.sh
```

Master 0 crashes while Worker 0 is processing, then load balancer retries Master 1:

```bash
./scripts/test_master_crash_during_processing_ollama.sh
```

Logs are written to `logs/`. PIDs are written to `.pids/`.
