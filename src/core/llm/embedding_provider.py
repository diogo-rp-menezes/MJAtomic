import os
from langchain_core.embeddings import Embeddings
from src.core.llm.rotating_embeddings import RotatingEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
from src.core.logger import logger

class EmbeddingProvider:
    def __init__(self):
        self.provider = os.getenv("EMBEDDING_PROVIDER", "google").lower()
        
        # Configurações para Google
        self.google_model_name = os.getenv("GOOGLE_EMBEDDING_MODEL", "gemini-embedding-001")
        
        # Configurações para Ollama
        self.ollama_model_name = os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6b")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def get_embeddings(self) -> Embeddings:
        """
        Retorna uma instância do modelo de embeddings configurado,
        suportando diferentes provedores (Google, Ollama).
        """
        if self.provider == "ollama":
            logger.info(f"Usando Ollama embeddings com o modelo: {self.ollama_model_name}")
            try:
                return OllamaEmbeddings(
                    model=self.ollama_model_name,
                    base_url=self.ollama_base_url
                )
            except Exception as e:
                logger.error(f"Falha ao inicializar OllamaEmbeddings: {e}")
                raise ValueError("Não foi possível conectar ao Ollama. Verifique se ele está em execução e acessível na URL configurada.")

        elif self.provider == "google":
            logger.info(f"Usando Google embeddings com o modelo: {self.google_model_name} e rotação de chaves.")
            return RotatingEmbeddings(model_name=self.google_model_name)
            
        else:
            raise ValueError(f"Provedor de embedding desconhecido ou não suportado: '{self.provider}'")
