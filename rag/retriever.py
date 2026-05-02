import os

import requests

from rag.vector_store import retrieve_context as retrieve_local_context


RAG_URL = os.getenv("RAG_URL")
RAG_TIMEOUT = float(os.getenv("RAG_TIMEOUT", "5"))


def retrieve_context(query: str) -> str:
    if RAG_URL:
        try:
            response = requests.get(
                f"{RAG_URL.rstrip('/')}/retrieve",
                params={"query": query},
                timeout=RAG_TIMEOUT
            )
            response.raise_for_status()
            return response.json().get("context", "")
        except requests.exceptions.RequestException as error:
            return f"RAG service unavailable: {error}"

    return retrieve_local_context(query)
