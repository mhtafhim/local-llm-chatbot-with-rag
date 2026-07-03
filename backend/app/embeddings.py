from chromadb.utils import embedding_functions

from app.llm.base import LLMProvider


class ProviderEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def __call__(self, input):
        return self.provider.embed(list(input))
