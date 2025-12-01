import os
from typing import List, Tuple
from langchain_postgres import PGVectorStore, PGEngine
from src.core.llm.embedding_provider import EmbeddingProvider
from src.core.logger import logger
import sqlalchemy

class VectorMemory:
    def __init__(self):
        self.embedding_provider = EmbeddingProvider()

        self.connection_string = os.getenv("POSTGRES_URL")
        if not self.connection_string:
            raise ValueError("A variável de ambiente POSTGRES_URL não está definida.")

        self.collection_name = os.getenv("PGVECTOR_COLLECTION_NAME", "code_collection")

        try:
             # Initialize PGEngine
             self.engine = PGEngine.from_connection_string(self.connection_string)

             # Initialize PGVectorStore
             self.store = PGVectorStore.create_sync(
                 engine=self.engine,
                 table_name=self.collection_name,
                 embedding_service=self.embedding_provider.get_embeddings()
             )
        except Exception as e:
            logger.error(f"Failed to initialize PGVectorStore: {e}")
            raise

    def search(self, query: str, k: int = 5) -> List[Tuple[str, dict]]:
        """
        Realiza uma busca por similaridade no banco de dados vetorial.
        """
        logger.info(f"Realizando busca por similaridade para a query: '{query[:50]}...'")
        try:
            documents = self.store.similarity_search_with_score(query, k=k)
            # Retorna no formato (texto, metadados) para consistência com a ferramenta
            return [(doc.page_content, doc.metadata) for doc, score in documents]
        except Exception as e:
            # Isso pode acontecer se a coleção ainda não existir ou erro de conexão
            logger.error(f"Erro durante a busca por similaridade: {e}")
            return []
