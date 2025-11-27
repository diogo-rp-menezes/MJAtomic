from typing import List, Optional

from langchain_community.vectorstores.pgvector import PGVector
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

from src.core.config.settings import settings


class VectorMemory:
    """
    Manages the vector store for RAG (Retrieval-Augmented Generation).
    """

    def __init__(self, collection_name: str = "dev_agent_memory", initialized: bool = True):
        self.collection_name = collection_name
        self._initialized = initialized
        if self._initialized:
            self.connection_string = self._get_connection_string()
            self.embedding_function = self._get_embedding_function()
            self.vector_store = self._get_vector_store()

    def is_initialized(self) -> bool:
        return self._initialized

    def _get_connection_string(self) -> str:
        return PGVector.connection_string_from_db_params(
            driver="psycopg2",
            host="postgres",
            port=5432,
            database="dev_agent_db",
            user="user",
            password="password",
        )

    def _get_embedding_function(self) -> Embeddings:
        # Using a local, open-source model for embeddings
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    def _get_vector_store(self) -> PGVector:
        return PGVector(
            collection_name=self.collection_name,
            connection_string=self.connection_string,
            embedding_function=self.embedding_function,
        )

    def add_documents(self, documents: List[Document]):
        """
        Adds a list of documents to the vector store.
        """
        if not self.is_initialized():
            return
        self.vector_store.add_documents(documents)

    def retrieve_context(self, query: str, k: int = 5) -> str:
        """
        Retrieves the top-k most relevant documents for a given query.
        """
        if not self.is_initialized():
            return "Memory not available."
        
        retriever = self.vector_store.as_retriever(search_kwargs={"k": k})
        docs = retriever.get_relevant_documents(query)
        return "\n".join([doc.page_content for doc in docs])
