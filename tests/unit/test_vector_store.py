import pytest
import os
from unittest.mock import patch, MagicMock
from src.core.memory.vector_store import VectorMemory

@patch.dict(os.environ, {"POSTGRES_URL": "postgresql://user:pass@localhost:5432/db"})
@patch("src.core.memory.vector_store.PGVectorStore")
@patch("src.core.memory.vector_store.PGEngine")
@patch("src.core.memory.vector_store.EmbeddingProvider")
def test_search(MockEmbed, MockPGEngine, MockPGVectorStore):
    # Mock return values
    mock_engine = MockPGEngine.from_connection_string.return_value
    mock_store_instance = MockPGVectorStore.create_sync.return_value

    # search returns [(doc, score)]
    mock_doc = MagicMock()
    mock_doc.page_content = "content"
    mock_doc.metadata = {"meta": "data"}
    mock_store_instance.similarity_search_with_score.return_value = [(mock_doc, 0.9)]

    mem = VectorMemory()
    results = mem.search("query")

    # Verification
    MockPGEngine.from_connection_string.assert_called_once()
    MockPGVectorStore.create_sync.assert_called_once()

    assert len(results) == 1
    assert results[0][0] == "content"
    assert results[0][1] == {"meta": "data"}

def test_init_missing_env():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="POSTGRES_URL"):
            VectorMemory()
