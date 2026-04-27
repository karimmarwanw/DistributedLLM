import time


def run_llm(query: str, context: str) -> str:
    """
    Fake llm inference for now.
    Later, replace this with Ollama/API/Hugging Face model.
    """

    # Simulate GPU/llm processing delay
    time.sleep(0.2)

    return f"llm answer for '{query}' using context: [{context}]"