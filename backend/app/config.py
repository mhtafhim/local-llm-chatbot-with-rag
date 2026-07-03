import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama").lower()

    ollama_base: str = os.getenv("OLLAMA_BASE", "http://localhost:11434").rstrip("/")
   # ollama_chat_model: str = os.getenv("OLLAMA_CHAT_MODEL", "gemma4:e2b")
    ollama_chat_model: str = os.getenv("OLLAMA_CHAT_MODEL", "hf.co/khazarai/Qwen3-4B-Qwen3.6-plus-Reasoning-Distilled-GGUF:latest")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    lmstudio_base: str = os.getenv("LMSTUDIO_BASE", "http://localhost:1234/v1").rstrip("/")
    lmstudio_chat_model: str | None = os.getenv("LMSTUDIO_CHAT_MODEL") or None
    lmstudio_embed_model: str = os.getenv(
        "LMSTUDIO_EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5"
    )

    docs_folder: str = os.getenv("DOCS_FOLDER", "./docs")
    chroma_path: str = os.getenv("CHROMA_PATH", "./chroma_db")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    top_k: int = int(os.getenv("TOP_K", "4"))


settings = Settings()
