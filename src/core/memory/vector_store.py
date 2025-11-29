import os
from typing import List, Tuple
from langchain_community.vectorstores.pgvector import PGVector
from src.core.llm.embedding_provider import EmbeddingProvider
from src.core.logger import logger

class VectorMemory:
    def __init__(self):
        self.embedding_provider = EmbeddingProvider()

        self.connection_string = os.getenv("POSTGRES_URL")
        if not self.connection_string:
            raise ValueError("A variável de ambiente POSTGRES_URL não está definida.")

        self.collection_name = os.getenv("PGVECTOR_COLLECTION_NAME", "code_collection")

        self.store = PGVector(
            connection_string=self.connection_string,
            embedding_function=self.embedding_provider.get_embeddings(),
            collection_name=self.collection_name,
        )

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
            # Isso pode acontecer se a coleção ainda não existir
            logger.error(f"Erro durante a busca por similaridade: {e}")
            return []
