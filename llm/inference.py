import os
import re
import time

import requests


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "300"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "300"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"


def has_relevant_context(context: str) -> bool:
    stripped_context = context.strip()
    no_context_prefixes = (
        "No relevant VectorDB context found",
        "No VectorDB context found",
        "RAG service unavailable"
    )

    return bool(stripped_context) and not stripped_context.startswith(no_context_prefixes)


def extract_context_source(context: str) -> str:
    match = re.search(r"\[source=([^\]\s]+)", context)

    if match:
        return match.group(1)

    return "the VectorDB"


def answer_prefix(context: str) -> str:
    if has_relevant_context(context):
        return f"I found relevant information in {extract_context_source(context)}: "

    return "I did not find relevant document context, but "


def build_prompt(query: str, context: str) -> str:
    if not has_relevant_context(context):
        return (
            "No relevant document context was found for this query. "
            "Answer from general knowledge only. Do not mention VectorDB, PDFs, "
            "documents, retrieved context, or whether context was found. The "
            "application will add that status message separately. Write only "
            "the answer body, complete and without stopping mid-sentence.\n\n"
            f"User query:\n{query}\n\n"
            "Answer:"
        )

    return (
        "You are answering inside a Retrieval-Augmented Generation system. "
        "Relevant context has already been retrieved automatically from the "
        "local vector database. Use that context as the primary source when it "
        "is relevant to the user query. Do not mention VectorDB, PDFs, source "
        "names, retrieved context, or whether context was found. The application "
        "will add the source message separately. Write only one clear answer to "
        "the user query, complete and without stopping mid-sentence.\n\n"
        f"Retrieved context:\n{context}\n\n"
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
        answer = data.get("response", "").strip()
        return f"{answer_prefix(context)}{answer}"
    except requests.exceptions.RequestException as error:
        return (
            "Ollama inference failed. "
            f"Reason: {error}. "
            f"Fallback: {run_simulated_llm(query, context)}"
        )
