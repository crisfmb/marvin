OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.1:8b"


def ask(prompt: str, model: str = DEFAULT_MODEL) -> str:
    payload = {"model": DEFAULT_MODEL, "prompt": prompt, "stream": False}
    print(payload)

    return f"Hello, {prompt}!"
