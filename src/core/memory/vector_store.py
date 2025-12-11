import os
from typing import List, Tuple
from langchain_postgres import PGVectorStore, PGEngine
from sqlalchemy import create_engine, text, inspect, Table, Column, String, MetaData, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
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

    def _ensure_table_structure(self, engine):
        """
        Garante que a tabela de vetores exista com o esquema EXATO necessário.
        Verifica se todas as colunas obrigatórias (langchain_id, content, embedding, cmetadata) existem.
        Se o esquema estiver incorreto, dropa a tabela e a recria.
        """
        try:
            insp = inspect(engine)
            table_exists = self.collection_name in insp.get_table_names()

            should_recreate = False
            required_columns = {"langchain_id", "content", "embedding", "cmetadata"}

            if table_exists:
                existing_columns = set(c["name"] for c in insp.get_columns(self.collection_name))
                missing_columns = required_columns - existing_columns

                if missing_columns:
                    logger.warning(f"Tabela '{self.collection_name}' está incompleta. Faltando colunas: {missing_columns}. Recriando...")
                    should_recreate = True
                else:
                    logger.debug(f"Tabela '{self.collection_name}' verificada e possui todas as colunas necessárias.")

            if should_recreate:
                # Dropa a tabela existente
                with engine.connect() as conn:
                    conn.execute(text(f"DROP TABLE IF EXISTS {self.collection_name} CASCADE"))
                    conn.commit()
                table_exists = False

            if not table_exists:
                logger.info(f"Criando tabela '{self.collection_name}' manualmente via SQLAlchemy...")
                metadata = MetaData()

                # Definição manual da tabela para garantir esquema correto
                # content: armazena o texto do documento
                # cmetadata: armazena metadados em formato JSONB
                # embedding: vetor de embeddings
                _ = Table(
                    self.collection_name,
                    metadata,
                    Column("langchain_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
                    Column("content", Text),
                    Column("embedding", Vector(None)),
                    Column("cmetadata", JSONB),
                    extend_existing=True
                )

                metadata.create_all(engine)
                logger.info(f"Tabela '{self.collection_name}' criada com sucesso com o esquema correto.")

        except Exception as e:
            logger.error(f"Erro ao garantir estrutura da tabela via SQLAlchemy: {e}")
            # Não lançamos exceção aqui para tentar deixar o PGVectorStore seguir seu fluxo se possível,
            # mas o erro é logado.
            raise e

    def _init_store(self, connection_string: str):
        try:
            # 1. Cria um engine padrão do SQLAlchemy para manutenção da estrutura
            #    Isso é necessário porque o PGEngine do langchain-postgres não é inspecionável
            #    diretamente pelo SQLAlchemy.
            maintenance_engine = create_engine(connection_string)
            self._ensure_table_structure(maintenance_engine)
            maintenance_engine.dispose()

            # 2. Cria o engine especializado da própria biblioteca langchain-postgres
            engine = PGEngine.from_connection_string(connection_string)

            # 3. Passa o engine para a PGVectorStore
            #   Mesmo que o create_sync tente criar, ele verá a tabela existente
            #   e deve respeitá-la.
            self.store = PGVectorStore.create_sync(
                engine=engine,
                embedding_service=self.embedding_provider.get_embeddings(),
                table_name=self.collection_name,
                id_column="langchain_id",
                metadata_json_column="cmetadata",
            )
            logger.info(f"VectorMemory inicializada com sucesso para a coleção '{self.collection_name}'.")
        except Exception as e:
            logger.error(f"Falha crítica ao inicializar PGVectorStore: {e}")
            raise

    def _self_heal_schema(self, connection_string: str):
        """
        Método de legado/fallback. A lógica principal agora está em _ensure_table_structure.
        """
        try:
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                logger.info(f"Dropando tabela '{self.collection_name}'...")
                conn.execute(text(f"DROP TABLE IF EXISTS {self.collection_name} CASCADE"))
                conn.commit()
            logger.info("Tabela removida.")
        except Exception as e:
            logger.error(f"Erro no self_heal: {e}")

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
