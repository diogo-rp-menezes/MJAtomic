import os
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.embeddings import Embeddings

class EmbeddingProvider:
    def __init__(self):
        self.provider = os.getenv("EMBEDDING_PROVIDER", "google").lower()
        self.model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

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
            return GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=os.getenv("GOOGLE_API_KEY")
            )
        else:
            raise ValueError(f"Provedor de embedding desconhecido: {self.provider}")
