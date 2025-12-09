import os
from typing import List, Tuple
from langchain_postgres import PGVectorStore, PGEngine
from sqlalchemy import create_engine, text
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

        self._init_store(connection_string)

    def _init_store(self, connection_string: str):
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
                id_column="langchain_id",
            )
            logger.info(f"VectorMemory inicializada com sucesso para a coleção '{self.collection_name}'.")
        except Exception as e:
            error_msg = str(e)
            if "Id column, langchain_id, does not exist" in error_msg:
                logger.warning(f"Detectada incompatibilidade de esquema na tabela '{self.collection_name}'. Iniciando auto-cura...")
                self._self_heal_schema(connection_string)

                # Tenta novamente após a cura
                logger.info("Tentando reinicializar VectorMemory após auto-cura...")
                try:
                    engine = PGEngine.from_connection_string(connection_string)
                    self.store = PGVectorStore.create_sync(
                        engine=engine,
                        embedding_service=self.embedding_provider.get_embeddings(),
                        table_name=self.collection_name,
                        id_column="langchain_id",
                    )
                    logger.info("VectorMemory recuperada e inicializada com sucesso.")
                except Exception as retry_e:
                    logger.error(f"Falha ao reinicializar VectorMemory após tentativa de auto-cura: {retry_e}")
                    raise retry_e
            else:
                logger.error(f"Falha crítica ao inicializar PGVectorStore: {e}")
                raise

    def _self_heal_schema(self, connection_string: str):
        """
        Remove a tabela de vetores corrompida/incompatível para permitir recriação limpa.
        """
        try:
            # Usa um engine genérico do SQLAlchemy para operações de DDL puras
            # Precisamos garantir que seja um engine compatível com o driver instalado

            # Ajuste para usar apenas psycopg (v3) que é o que temos instalado
            # O connection_string já foi normalizado em __init__
            engine = create_engine(connection_string)

            with engine.connect() as conn:
                logger.info(f"Dropando tabela '{self.collection_name}'...")
                conn.execute(text(f"DROP TABLE IF EXISTS {self.collection_name} CASCADE"))
                conn.commit()

            logger.info("Tabela de vetores removida com sucesso. O esquema será recriado na próxima inicialização.")

        except Exception as e:
            logger.error(f"Erro durante o processo de auto-cura do esquema: {e}")
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
