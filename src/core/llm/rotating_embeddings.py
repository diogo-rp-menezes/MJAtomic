from typing import List
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
import time

class RotatingEmbeddings(Embeddings):
    """
    A wrapper around GoogleGenerativeAIEmbeddings that rotates API keys on every call.
    """
    def __init__(self, model_name: str = "models/embedding-001"):
        self.model_name = model_name
        self.keys = self._load_api_keys()
        self.current_key_index = 0
        self.provider = "google"

    def _load_api_keys(self) -> List[str]:
        keys = []
        main_key = os.getenv("GOOGLE_API_KEY")
        if main_key:
            keys.append(main_key)
        for i in range(1, 11):
            k = os.getenv(f"GOOGLE_API_KEY_{i}")
            if k:
                keys.append(k)
        if not keys:
             return ["mock-key"]
        return keys

    def _get_next_key(self) -> str:
        if not self.keys:
            return ""
        key = self.keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        return key

    def _get_embedding_model(self) -> Embeddings:
        current_key = self._get_next_key()
        return GoogleGenerativeAIEmbeddings(
            model=self.model_name,
            google_api_key=current_key
        )

    def _apply_delay(self):
        try:
            delay = float(os.getenv("REQUEST_DELAY_SECONDS", "1"))
            if delay > 0:
                time.sleep(delay)
        except (ValueError, TypeError):
            time.sleep(1)

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
