import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.1:8b"


def ask(prompt: str, model: str = DEFAULT_MODEL) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    response = httpx.post(OLLAMA_URL, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["response"]
