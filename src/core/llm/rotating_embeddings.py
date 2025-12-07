from typing import List
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
import time
from src.core.llm.api_key_manager import key_manager

class RotatingEmbeddings(Embeddings):
    """
    A wrapper around GoogleGenerativeAIEmbeddings that rotates API keys on every call.
    """
    def __init__(self, model_name: str = "models/embedding-001"):
        self.model_name = model_name
        self.provider = "google"

    def _get_embedding_model(self) -> Embeddings:
        current_key = key_manager.get_next_key()
        return GoogleGenerativeAIEmbeddings(
            model=self.model_name,
            google_api_key=current_key
        )

    def _apply_delay(self):
        # We rely on ApiKeyManager for rate limiting now, but keeping this
        # for extra safety if REQUEST_DELAY_SECONDS is explicitly set.
        try:
            delay = float(os.getenv("REQUEST_DELAY_SECONDS", "0"))
            if delay > 0:
                time.sleep(delay)
        except (ValueError, TypeError):
            pass

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs."""
        try:
            result = self._get_embedding_model().embed_documents(texts)
            return result
        finally:
            self._apply_delay()

    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""
        try:
            result = self._get_embedding_model().embed_query(text)
            return result
        finally:
            self._apply_delay()
