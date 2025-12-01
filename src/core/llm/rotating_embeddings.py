from typing import List, Optional
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os

class RotatingEmbeddings(Embeddings):
    """
    A wrapper around GoogleGenerativeAIEmbeddings that rotates API keys on every call.
    """
    def __init__(self, model_name: str = "models/embedding-001"):
        self.model_name = model_name
        self.keys = self._load_api_keys()
        self.current_key_index = 0
        self.provider = "google" # Hardcoded for now as per plan, but can be flexible

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
             # Fallback/Mock for testing environments without keys
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

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs."""
        return self._get_embedding_model().embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""
        return self._get_embedding_model().embed_query(text)
