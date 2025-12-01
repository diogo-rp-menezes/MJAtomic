import os
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.embeddings import Embeddings
from typing import List

class EmbeddingProvider:
    def __init__(self):
        self.provider = os.getenv("EMBEDDING_PROVIDER", "google").lower()
        self.model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.keys = self._load_api_keys()
        self.current_key_index = 0

    def _load_api_keys(self) -> List[str]:
        keys = []
        main_key = os.getenv("GOOGLE_API_KEY")
        if main_key:
            keys.append(main_key)
        for i in range(1, 11):
            k = os.getenv(f"GOOGLE_API_KEY_{i}")
            if k:
                keys.append(k)
        if not keys and self.provider == "google":
             return ["mock-key"]
        return keys

    def _get_next_key(self) -> str:
        if not self.keys:
            return ""
        key = self.keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        return key

    def get_embeddings(self) -> Embeddings:
        """
        Retorna uma instância do modelo de embeddings configurado.
        """
        if self.provider == "openai":
            return OpenAIEmbeddings(
                api_key=os.getenv("OPENAI_API_KEY"),
                model=self.model_name
            )
        elif self.provider == "google":
            # O modelo de embedding do Google é especificado na própria chamada
            current_key = self._get_next_key()
            return GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=current_key
            )
        else:
            raise ValueError(f"Provedor de embedding desconhecido: {self.provider}")
