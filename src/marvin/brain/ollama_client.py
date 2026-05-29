import httpx

DEFAULT_MODEL = "llama3.1:8b"
DEFAULT_URL = "http://localhost:11434/api/generate"


class OllamaClient:
    def __init__(self, model: str = DEFAULT_MODEL, url: str = DEFAULT_URL) -> None:
        self.model = model
        self.url = url

    def ask(self, prompt: str) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        response = httpx.post(self.url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["response"]
