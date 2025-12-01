import pytest
import os
from unittest.mock import patch, MagicMock
from src.core.memory.vector_store import VectorMemory

@patch.dict(os.environ, {"POSTGRES_URL": "postgresql://user:pass@localhost:5432/db"})
@patch("src.core.memory.vector_store.PGVector")
@patch("src.core.memory.vector_store.EmbeddingProvider")
def test_search(MockEmbed, MockPGVector):
    mock_store = MockPGVector.return_value
    # search returns [(doc, score)]
    mock_doc = MagicMock()
    mock_doc.page_content = "content"
    mock_doc.metadata = {"meta": "data"}
    mock_store.similarity_search_with_score.return_value = [(mock_doc, 0.9)]

    mem = VectorMemory()
    results = mem.search("query")

    assert len(results) == 1
    assert results[0][0] == "content"
    assert results[0][1] == {"meta": "data"}

def test_init_missing_env():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="POSTGRES_URL"):
            VectorMemory()
