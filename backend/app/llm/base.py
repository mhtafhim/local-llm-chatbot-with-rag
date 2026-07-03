from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any


class LLMProvider(ABC):
    name: str
    base_url: str
    chat_model: str | None
    embed_model: str

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""

    @abstractmethod
    def chat_stream(self, messages: list[dict[str, str]]) -> Iterable[bytes]:
        """Yield OpenAI-compatible server-sent event bytes."""

    @abstractmethod
    def get_chat_model(self) -> str:
        """Return the configured or detected chat model name."""

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "base_url": self.base_url,
            "chat_model": self.get_chat_model(),
            "embed_model": self.embed_model,
        }
