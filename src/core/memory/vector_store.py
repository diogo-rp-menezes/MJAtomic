import os
from typing import List, Tuple
from langchain_postgres import PGVectorStore
from src.core.llm.embedding_provider import EmbeddingProvider
from src.core.logger import logger

class VectorMemory:
    def __init__(self):
        self.embedding_provider = EmbeddingProvider()

        self.connection_string = os.getenv("POSTGRES_URL")
        if not self.connection_string:
            raise ValueError("A variável de ambiente POSTGRES_URL não está definida.")

        # Ensure correct protocol for psycopg3
        if "postgresql+psycopg2://" in self.connection_string:
             self.connection_string = self.connection_string.replace("postgresql+psycopg2://", "postgresql+psycopg://")
        elif "postgresql://" in self.connection_string:
             self.connection_string = self.connection_string.replace("postgresql://", "postgresql+psycopg://")

        self.collection_name = os.getenv("PGVECTOR_COLLECTION_NAME", "code_collection")

        try:
            self.store = PGVectorStore.create_sync(
                connection_string=self.connection_string,
                embedding_service=self.embedding_provider.get_embeddings(),
                table_name=self.collection_name,
            )
        except Exception as e:
            logger.error(f"Error initializing PGVectorStore: {e}")
            raise

    def search(self, query: str, k: int = 5) -> List[Tuple[str, dict]]:
        """
        Realiza uma busca por similaridade no banco de dados vetorial.
        """
        logger.info(f"Realizando busca por similaridade para a query: '{query[:50]}...'")
        try:
            documents = self.store.similarity_search_with_score(query, k=k)
            return [(doc.page_content, doc.metadata) for doc, score in documents]
        except Exception as e:
            logger.error(f"Erro durante a busca por similaridade: {e}")
            return []
