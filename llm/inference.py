import time


def run_llm(query: str, context: str) -> str:
    time.sleep(0.2)
    return f"LLM response for '{query}' using context: {context}"