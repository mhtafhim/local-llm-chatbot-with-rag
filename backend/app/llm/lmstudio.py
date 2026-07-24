import json
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

    def chat_stream(
        self, messages: list[dict[str, str]], thinking: bool = True
    ) -> Iterable[bytes]:
        with requests.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.get_chat_model(),
                "messages": messages,
                "stream": True,
                # Respected by llama.cpp-based servers (e.g. LM Studio) for
                # models with a switchable chat template, such as Qwen3.
                # Ignored harmlessly by servers/models that don't support it.
                "chat_template_kwargs": {"enable_thinking": thinking},
            },
            stream=True,
            timeout=300,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                if thinking:
                    yield line + b"\n"
                else:
                    yield from self._strip_reasoning(line)

    @staticmethod
    def _strip_reasoning(line: bytes) -> Iterable[bytes]:
        """Drop reasoning/thinking deltas for backends that ignore enable_thinking."""
        text = line.decode("utf-8", errors="ignore")
        if not text.startswith("data:") or text[len("data:"):].strip() == "[DONE]":
            yield line + b"\n"
            return

        try:
            chunk = json.loads(text[len("data:"):].strip())
        except ValueError:
            yield line + b"\n"
            return

        stripped = False
        for choice in chunk.get("choices", []):
            delta = choice.get("delta", {})
            for key in ("reasoning_content", "reasoning"):
                if key in delta:
                    del delta[key]
                    stripped = True

        if not stripped:
            yield line + b"\n"
            return

        choices = chunk.get("choices", [])
        if choices and not choices[0].get("delta") and choices[0].get("finish_reason") is None:
            return

        yield f"data: {json.dumps(chunk)}\n\n".encode("utf-8")
