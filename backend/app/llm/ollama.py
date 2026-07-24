import json
from collections.abc import Iterable

import requests

from app.config import Settings
from app.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, settings: Settings):
        self.base_url = settings.ollama_base
        self.chat_model = settings.ollama_chat_model
        self.embed_model = settings.ollama_embed_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            resp = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.embed_model, "input": text},
                timeout=60,
            )
            if resp.status_code == 404:
                resp = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.embed_model, "prompt": text},
                    timeout=60,
                )
            resp.raise_for_status()
            data = resp.json()
            if "embeddings" in data:
                embeddings.append(data["embeddings"][0])
            else:
                embeddings.append(data["embedding"])
        return embeddings

    def get_chat_model(self) -> str:
        if self.chat_model:
            return self.chat_model
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            for model in resp.json().get("models", []):
                name = model.get("name", "")
                if name and "embed" not in name.lower():
                    return name
        except Exception:
            pass
        return "llama3.1"

    def chat_stream(
        self, messages: list[dict[str, str]], thinking: bool = True
    ) -> Iterable[bytes]:
        with requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.get_chat_model(),
                "messages": messages,
                "stream": True,
                "think": thinking,
            },
            stream=True,
            timeout=300,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line.decode("utf-8"))
                message = chunk.get("message", {})
                reasoning_text = message.get("thinking", "")
                content = message.get("content", "")
                if reasoning_text and thinking:
                    payload = {
                        "choices": [{"delta": {"reasoning_content": reasoning_text}}]
                    }
                    yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
                if content:
                    payload = {"choices": [{"delta": {"content": content}}]}
                    yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
                if chunk.get("done"):
                    yield b"data: [DONE]\n\n"
