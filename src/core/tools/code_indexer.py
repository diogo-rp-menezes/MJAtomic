import os
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores.pgvector import PGVector
from langchain_core.documents import Document

from src.core.config.settings import settings


class CodeIndexerTool:
    """
    Tool for indexing the entire codebase into a vector store.
    """

    def __init__(self, vector_store: PGVector):
        self.vector_store = vector_store
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )

    def index_workspace(self, workspace_path: str = settings.WORKSPACE_PATH):
        """
        Walks through the workspace directory and indexes all files.
        """
        all_docs: List[Document] = []
        for root, _, files in os.walk(workspace_path):
            for file in files:
                if self._should_index(file):
                    file_path = os.path.join(root, file)
                    docs = self._load_and_split_document(file_path)
                    if docs:
                        all_docs.extend(docs)

        if all_docs:
            self.vector_store.add_documents(all_docs)

    def _should_index(self, file_name: str) -> bool:
        """
        Determines if a file should be indexed based on its extension.
        """
        # A simple filter to avoid indexing binary files, etc.
        valid_extensions = {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".html", ".css", ".js"}
        return any(file_name.endswith(ext) for ext in valid_extensions)

    def _load_and_split_document(self, file_path: str) -> List[Document] | None:
        """
        Loads a document from a file path and splits it into chunks.
        """
        try:
            loader = TextLoader(file_path, encoding="utf-8")
            documents = loader.load()
            return self.text_splitter.split_documents(documents)
        except Exception as e:
            print(f"Error loading or splitting document {file_path}: {e}")
            return None
