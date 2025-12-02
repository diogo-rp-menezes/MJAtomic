import pytest
import os
from unittest.mock import patch, MagicMock
from src.core.memory.indexer import CodeIndexer

@patch.dict(os.environ, {"POSTGRES_URL": "postgresql://user:pass@localhost:5432/db"})
@patch("src.core.memory.indexer.PGEngine")
@patch("src.core.memory.indexer.PGVectorStore")
@patch("src.core.memory.indexer.RecursiveCharacterTextSplitter")
@patch("src.core.memory.indexer.DirectoryLoader")
@patch("src.core.memory.indexer.EmbeddingProvider")
def test_index_workspace(MockEmbed, MockLoader, MockSplitter, MockPGVectorStore, MockPGEngine, tmp_path):
    # Setup
    mock_loader_instance = MockLoader.return_value
    mock_loader_instance.load.return_value = ["doc"]

    mock_splitter = MockSplitter.return_value
    mock_splitter.split_documents.return_value = ["split"]

    mock_store = MagicMock()
    MockPGVectorStore.create_sync.return_value = mock_store

    indexer = CodeIndexer(workspace_path=str(tmp_path))
    indexer.index_workspace()

    # Verification
    MockPGEngine.from_connection_string.assert_called_once()
    MockPGVectorStore.create_sync.assert_called_once()
    mock_store.add_documents.assert_called_once_with(["split"])

def test_index_workspace_invalid_path():
    with pytest.raises(ValueError):
        CodeIndexer(workspace_path="/non/existent/path")
