"""Thin client for a networked Ollama server's /api/generate endpoint."""

import requests


class OllamaClient:
    def __init__(self, host: str, model: str, timeout: float = 60.0):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, system: str = None, temperature: float = 0.7) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        response = requests.post(f"{self.host}/api/generate", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()["response"].strip()
