import os
from typing import List

from langchain_postgres import PGVectorStore, PGEngine
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document


class DummyEmbeddings(Embeddings):
    """Embeddings de teste (sem chamadas externas)."""

    def __init__(self, dim: int = 768):
        self.dim = dim

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.0] * self.dim for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        return [0.0] * self.dim


def main():
    table = os.getenv("PGVECTOR_COLLECTION_NAME", "code_collection")
    conn = os.getenv("POSTGRES_URL")
    if not conn:
        raise SystemExit("POSTGRES_URL não definido no ambiente")

    # Normaliza para psycopg3 se necessário
    if conn.startswith("postgresql+psycopg2://"):
        conn = conn.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    elif conn.startswith("postgresql://"):
        conn = conn.replace("postgresql://", "postgresql+psycopg://", 1)

    print("[quick_test_vector] DSN:", conn)
    print("[quick_test_vector] Tabela:", table)

    engine = PGEngine.from_connection_string(conn)
    store = PGVectorStore.create_sync(
        engine=engine,
        embedding_service=DummyEmbeddings(dim=768),
        table_name=table,
    )
    print("[quick_test_vector] PGVectorStore criado com sucesso.")

    # Grava um documento de teste
    docs = [Document(page_content="hello world", metadata={"source": "quick_test"})]
    store.add_documents(docs)
    print("[quick_test_vector] Documento de teste adicionado.")


if __name__ == "__main__":
    main()
