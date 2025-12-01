import os
from langchain_core.embeddings import Embeddings
from src.core.llm.rotating_embeddings import RotatingEmbeddings

class EmbeddingProvider:
    def __init__(self):
        self.provider = os.getenv("EMBEDDING_PROVIDER", "google").lower()
        self.model_name = os.getenv("EMBEDDING_MODEL", "models/embedding-001")
        # Logic for keys rotation is now inside RotatingEmbeddings

    def get_embeddings(self) -> Embeddings:
        """
        Retorna uma instância do modelo de embeddings configurado.
        Agora usa RotatingEmbeddings para garantir rotação de chaves.
        """
        if self.provider == "google":
            return RotatingEmbeddings(model_name=self.model_name)
        else:
            # Fallback or other providers not implemented with rotation yet
            raise ValueError(f"Provedor de embedding desconhecido ou sem suporte a rotação: {self.provider}")
