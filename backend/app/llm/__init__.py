from app.config import Settings
from app.llm.lmstudio import LMStudioProvider
from app.llm.ollama import OllamaProvider


def create_provider(settings: Settings):
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings)
    if settings.llm_provider in {"lmstudio", "lm_studio", "lm-studio"}:
        return LMStudioProvider(settings)
    raise ValueError(
        f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. Use 'ollama' or 'lmstudio'."
    )
