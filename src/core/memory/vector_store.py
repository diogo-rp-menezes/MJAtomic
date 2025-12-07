import os
from typing import List, Tuple
from langchain_postgres import PGVectorStore, PGEngine
from src.core.llm.embedding_provider import EmbeddingProvider
from src.core.logger import logger
from src.core.config import settings

class VectorMemory:
    def __init__(self):
        """
        Inicializa a memória vetorial criando seu próprio PGEngine.
        Com apenas o driver 'psycopg' (v3) instalado, não há ambiguidade
        e a biblioteca selecionará o driver async correto.
        """
        self.embedding_provider = EmbeddingProvider()
        self.collection_name = settings.PGVECTOR_COLLECTION_NAME

        connection_string = settings.POSTGRES_URL
        if not connection_string:
            raise ValueError("A variável de ambiente POSTGRES_URL não está definida.")

        # Normaliza para driver psycopg3 quando necessário para evitar carregar psycopg2 síncrono
        if connection_string.startswith("postgresql+psycopg2://"):
            connection_string = connection_string.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
        elif connection_string.startswith("postgresql://"):
            connection_string = connection_string.replace("postgresql://", "postgresql+psycopg://", 1)

        try:
            # 1. Cria o engine especializado da própria biblioteca langchain-postgres
            engine = PGEngine.from_connection_string(connection_string)

            # 2. Passa o engine especializado para a PGVectorStore
            #   Observação: versões atuais do langchain-postgres usam
            #   'collection_name' e não aceitam 'id_key'.
            self.store = PGVectorStore.create_sync(
                engine=engine,
                embedding_service=self.embedding_provider.get_embeddings(),
                table_name=self.collection_name,
            )
            logger.info(f"VectorMemory inicializada com sucesso para a coleção '{self.collection_name}'.")
        except Exception as e:
            logger.error(f"Falha crítica ao inicializar PGVectorStore: {e}")
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
