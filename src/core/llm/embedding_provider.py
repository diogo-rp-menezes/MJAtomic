import os
import json
import urllib.request
import urllib.error
from typing import List
from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings
from src.core.llm.rotating_embeddings import RotatingEmbeddings
from src.core.logger import logger
from src.core.config import settings

class LocalOpenAIEmbeddings(Embeddings):
    """
    Custom Embeddings class to interact with OpenAI-compatible APIs (like LM Studio)
    using standard library, avoiding 'openai' package dependency.
    """
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url.rstrip('/')
        if not self.base_url.endswith("/v1"):
            self.base_url += "/v1"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs."""
        # OpenAI API supports batching in 'input'
        return self._embed_batch(texts)

    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""
        result = self._embed_batch([text])
        return result[0] if result else []

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.base_url}/embeddings"

        payload = {
            "model": self.model,
            "input": texts
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer lm-studio" # Dummy key
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req) as response:
                result = json.load(response)
                # Parse OpenAI format: { "data": [ { "embedding": [...], "index": 0 }, ... ] }
                data_items = result.get("data", [])
                # Ensure sorted by index just in case
                data_items.sort(key=lambda x: x.get("index", 0))
                return [item["embedding"] for item in data_items]

        except urllib.error.URLError as e:
            logger.error(f"Failed to connect to Local OpenAI Embeddings at {url}: {e}")
            raise ValueError(f"Failed to connect to Local OpenAI Embeddings at {url}: {e}")


class EmbeddingProvider:
    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER
        
        # Configurações para Google
        self.google_model_name = settings.GOOGLE_EMBEDDING_MODEL
        
        # Configurações para Ollama / Local
        self.ollama_model_name = settings.OLLAMA_EMBEDDING_MODEL

        # [FIX] Prioriza URL específica de embedding, senão usa a geral
        self.ollama_base_url = settings.OLLAMA_EMBEDDING_URL or settings.OLLAMA_BASE_URL

    def get_embeddings(self) -> Embeddings:
        """
        Retorna uma instância do modelo de embeddings configurado,
        suportando diferentes provedores (Google, Ollama, URL Local).
        """
        # Se o provider for uma URL, usamos a lógica OpenAI Compatible (LM Studio, etc)
        if self.provider.startswith("http"):
            target_url = self.provider
            logger.info(f"Usando Local/OpenAI Embeddings com o modelo: {self.ollama_model_name} em {target_url}")
            return LocalOpenAIEmbeddings(
                model=self.ollama_model_name,
                base_url=target_url
            )

        elif self.provider == "ollama":
            # Usa OllamaEmbeddings nativo do langchain_ollama
            logger.info(f"Usando Ollama embeddings com o modelo: {self.ollama_model_name} em {self.ollama_base_url}")
            try:
                return OllamaEmbeddings(
                    model=self.ollama_model_name,
                    base_url=self.ollama_base_url
                )
            except Exception as e:
                logger.error(f"Falha ao inicializar OllamaEmbeddings: {e}")
                raise ValueError("Não foi possível conectar ao provedor de Embeddings local (Ollama). Verifique a URL.")

        elif self.provider == "local":
            if not self.ollama_base_url:
                raise ValueError("A variável de ambiente OLLAMA_BASE_URL é necessária para o provedor de embedding 'local'")

            logger.info(f"Usando Local Embeddings (via LocalOpenAIEmbeddings) com modelo: {self.ollama_model_name} em {self.ollama_base_url}")
            return LocalOpenAIEmbeddings(
                model=self.ollama_model_name,
                base_url=self.ollama_base_url
            )

        elif self.provider == "google":
            logger.info(f"Usando Google embeddings com o modelo: {self.google_model_name} e rotação de chaves.")
            return RotatingEmbeddings(model_name=self.google_model_name)
            
        else:
            raise ValueError(f"Provedor de embedding desconhecido ou não suportado: '{self.provider}'")
