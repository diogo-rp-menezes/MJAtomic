import os
import sys
import logging
import argparse
from typing import List

# Ensure src is in pythonpath
sys.path.append(os.getcwd())

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_postgres import PGVectorStore, PGEngine
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sqlalchemy import create_engine, text, inspect, Table, Column, MetaData, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

from src.core.config import settings
from src.core.llm.embedding_provider import EmbeddingProvider

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FakeEmbeddings(Embeddings):
    """Fake embeddings for testing."""
    def __init__(self, size: int = 768):
        self.size = size

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[1.0] * self.size for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        return [1.0] * self.size

def ensure_table_structure(connection_string, collection_name):
    """
    Manually creates the table with the correct schema (langchain_id)
    to match VectorMemory expectations.
    """
    engine = create_engine(connection_string)
    try:
        # Enable pgvector extension first
        with engine.connect() as conn:
             conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
             conn.commit()

        insp = inspect(engine)
        table_exists = collection_name in insp.get_table_names()

        should_recreate = False
        if table_exists:
            existing_columns = set(c["name"] for c in insp.get_columns(collection_name))
            if "langchain_id" not in existing_columns:
                logger.warning(f"Table {collection_name} exists but missing 'langchain_id'. Dropping...")
                should_recreate = True
            # Also check for cmetadata if we are enforcing it
            if "cmetadata" not in existing_columns:
                logger.warning(f"Table {collection_name} exists but missing 'cmetadata'. Dropping...")
                should_recreate = True

        if should_recreate:
            with engine.connect() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {collection_name} CASCADE"))
                conn.commit()
            table_exists = False

        if not table_exists:
            logger.info(f"Creating table '{collection_name}' manually...")
            metadata = MetaData()
            _ = Table(
                collection_name,
                metadata,
                Column("langchain_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
                Column("content", Text),
                Column("embedding", Vector(None)), # Dimension will be inferred or NULL
                Column("cmetadata", JSONB),
                extend_existing=True
            )
            metadata.create_all(engine)
            logger.info("Table created successfully.")

    except Exception as e:
        logger.error(f"Error ensuring table structure: {e}")
        raise e
    finally:
        engine.dispose()

def seed_knowledge_base(mock: bool = False):
    file_path = "referencias/MJProjectGeneratorReferencias.txt"
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    # 1. Read Content
    logger.info(f"Reading file: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 2. Split by Headers
    logger.info("Splitting content by Markdown headers...")
    headers_to_split_on = [
        ("#", "topic"),
        ("##", "subtopic"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(content)

    logger.info(f"Initial splits generated: {len(md_header_splits)}")

    # 3. Post-process and Add Metadata
    documents = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)

    for doc in md_header_splits:
        # Determine main topic. Priority: subtopic > topic > Unknown (Prefer specific section)
        topic = doc.metadata.get("subtopic") or doc.metadata.get("topic") or "General Engineering"

        base_metadata = {
            "source": "knowledge_base",
            "type": "guide",
            "topic": topic
        }

        final_metadata = {**doc.metadata, **base_metadata}

        if len(doc.page_content) > 2000:
            logger.info(f"Chunk for topic '{topic}' is too large. Splitting further...")
            sub_docs = text_splitter.create_documents([doc.page_content], metadatas=[final_metadata])
            documents.extend(sub_docs)
        else:
            doc.metadata = final_metadata
            documents.append(doc)

    logger.info(f"Final document chunks to index: {len(documents)}")
    for i, d in enumerate(documents):
        logger.info(f"Doc {i} Metadata: {d.metadata}")

    # 4. Connect to DB and Index
    connection_string = settings.POSTGRES_URL
    collection_name = settings.PGVECTOR_COLLECTION_NAME

    if not connection_string:
         logger.error("POSTGRES_URL not set.")
         sys.exit(1)

    if "postgresql+psycopg2://" in connection_string:
        connection_string = connection_string.replace("postgresql+psycopg2://", "postgresql+psycopg://")
    elif connection_string.startswith("postgresql://"):
        connection_string = connection_string.replace("postgresql://", "postgresql+psycopg://")

    logger.info(f"Connecting to Vector DB: {collection_name}")

    try:
        # Ensure schema is correct before langchain tries anything
        ensure_table_structure(connection_string, collection_name)

        if mock:
            logger.warning("Using MOCK embeddings (FakeEmbeddings).")
            embeddings = FakeEmbeddings(size=768)
        else:
            embedding_provider = EmbeddingProvider()
            embeddings = embedding_provider.get_embeddings()

        engine = PGEngine.from_connection_string(connection_string)
        store = PGVectorStore.create_sync(
            engine=engine,
            embedding_service=embeddings,
            table_name=collection_name,
            id_column="langchain_id",
            metadata_json_column="cmetadata"  # Matches VectorMemory schema
        )

        logger.info("Adding documents to vector store...")
        store.add_documents(documents)
        logger.info("Knowledge base seeding completed successfully.")

    except Exception as e:
        logger.error(f"Failed to index documents: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed knowledge base into Vector DB.")
    parser.add_argument("--mock", action="store_true", help="Use mock embeddings for testing.")
    args = parser.parse_args()

    seed_knowledge_base(mock=args.mock)
