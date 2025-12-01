import pytest
import os
from unittest.mock import patch, MagicMock
from src.core.memory.indexer import CodeIndexer

@patch.dict(os.environ, {"POSTGRES_URL": "postgresql://user:pass@localhost:5432/db"})
@patch("src.core.memory.indexer.PGVector")
@patch("src.core.memory.indexer.RecursiveCharacterTextSplitter")
@patch("src.core.memory.indexer.DirectoryLoader")
@patch("src.core.memory.indexer.EmbeddingProvider")
def test_index_workspace(MockEmbed, MockLoader, MockSplitter, MockPGVector, tmp_path):
    # Setup
    mock_loader_instance = MockLoader.return_value
    mock_loader_instance.load.return_value = ["doc"]

    mock_splitter = MockSplitter.return_value
    mock_splitter.split_documents.return_value = ["split"]

    indexer = CodeIndexer(workspace_path=str(tmp_path))
    indexer.index_workspace()

    MockPGVector.from_documents.assert_called_once()

def test_index_workspace_invalid_path():
    with pytest.raises(ValueError):
        CodeIndexer(workspace_path="/non/existent/path")
