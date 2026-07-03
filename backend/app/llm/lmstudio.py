from collections.abc import Iterable

import requests

from app.config import Settings
from app.llm.base import LLMProvider


class LMStudioProvider(LLMProvider):
    name = "lmstudio"

    def __init__(self, settings: Settings):
        self.base_url = settings.lmstudio_base
        self.chat_model = settings.lmstudio_chat_model
        self.embed_model = settings.lmstudio_embed_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            resp = requests.post(
                f"{self.base_url}/embeddings",
                json={"model": self.embed_model, "input": text},
                timeout=60,
            )
            resp.raise_for_status()
            embeddings.append(resp.json()["data"][0]["embedding"])
        return embeddings

    def get_chat_model(self) -> str:
        if self.chat_model:
            return self.chat_model
        try:
            resp = requests.get(f"{self.base_url}/models", timeout=10)
            resp.raise_for_status()
            for model in resp.json().get("data", []):
                name = model.get("id", "")
                if name and "embed" not in name.lower():
                    return name
        except Exception:
            pass
        return "local-model"

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterable[bytes]:
        with requests.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.get_chat_model(),
                "messages": messages,
                "stream": True,
            },
            stream=True,
            timeout=300,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    yield line + b"\n"
