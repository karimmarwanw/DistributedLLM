# Scenario Scripts

Run all scripts from the project root or directly by path.

## Start / Stop

```bash
./scripts/start_simulation_system.sh
./scripts/start_ollama_system.sh
./scripts/start_adam_distributed.sh
./scripts/start_karim_distributed.sh
./scripts/stop_adam_distributed.sh
./scripts/stop_karim_distributed.sh
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
./scripts/test_distributed_single.sh "why are threads useful in distributed systems?"
./scripts/test_distributed_10.sh "why are threads useful in distributed systems?"
./scripts/test_distributed_distribution_10.sh
./scripts/test_distributed_load.sh 10
./scripts/test_distributed_strategies.sh 10
./scripts/test_distributed_rag_retrieval.sh "what is process context?"
./scripts/check_distributed_network.sh
./scripts/test_distribution_10.sh
./scripts/test_load_simulation.sh 1000
./scripts/test_strategies.sh 100
```

Inference test output includes latency, throughput, master-node GPU utilization, master distribution, and worker distribution.

For two-MacBook mode, run `start_adam_distributed.sh` on `Adams-MacBook-Pro.local` first, then run `start_karim_distributed.sh` on `karims-macbook-pro.local`. The distributed setup uses `llama3.2:1b` on Karim and `phi:2.7b` on Adam by default.

RAG defaults to port `7100` because macOS often uses `7000` for system services. Start Adam normally with:

```bash
./scripts/start_adam_distributed.sh
./scripts/inject_pdf.sh "/Users/adamheshmatmakram/Downloads/3-Processes.pdf"
```

From Karim, distributed RAG checks use port `7100` by default:

```bash
./scripts/check_distributed_network.sh
./scripts/test_distributed_rag_retrieval.sh "what is process context?"
```

## Fault Tolerance

Distributed fault-tolerance tests for the two-MacBook setup:

```bash
./scripts/test_distributed_worker_failover_karim.sh
./scripts/test_distributed_worker_failover_adam.sh
./scripts/test_distributed_master_down_failover.sh
./scripts/test_distributed_master_crash_during_processing.sh
./scripts/test_distributed_single_worker_master_failover.sh
```

Local single-Mac fault-tolerance tests:

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
