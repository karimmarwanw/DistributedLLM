import os
import time

import requests


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "80"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"


def build_prompt(query: str, context: str) -> str:
    return (
        "Answer the user query using the provided context.\n\n"
        f"Context:\n{context}\n\n"
        f"User query:\n{query}\n\n"
        "Answer:"
    )


def run_simulated_llm(query: str, context: str) -> str:
    time.sleep(0.2)
    return f"Simulated LLM response for '{query}' using context: {context}"


def run_llm(query: str, context: str, max_tokens: int | None = None) -> str:
    if not USE_OLLAMA:
        return run_simulated_llm(query, context)

    num_predict = max_tokens or OLLAMA_NUM_PREDICT

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": build_prompt(query, context),
        "stream": False,
        "options": {
            "num_predict": num_predict,
            "temperature": OLLAMA_TEMPERATURE
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except requests.exceptions.RequestException as error:
        return (
            "Ollama inference failed. "
            f"Reason: {error}. "
            f"Fallback: {run_simulated_llm(query, context)}"
        )
