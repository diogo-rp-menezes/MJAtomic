import os
from unittest.mock import MagicMock, patch, ANY
import pytest

# Set environment variables before importing settings
os.environ["POSTGRES_USER"] = "test_user"
os.environ["POSTGRES_PASSWORD"] = "test_pass"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["REDIS_HOST"] = "localhost"
os.environ["POSTGRES_URL"] = "postgresql+psycopg://test_user:test_pass@localhost:5432/test_db"

from src.core.memory.vector_store import VectorMemory
from src.core.config import settings

@pytest.fixture
def mock_embedding_provider():
    with patch("src.core.memory.vector_store.EmbeddingProvider") as mock:
        yield mock

@pytest.fixture
def mock_pg_engine():
    with patch("src.core.memory.vector_store.PGEngine") as mock:
        yield mock

@pytest.fixture
def mock_pg_vector_store():
    with patch("src.core.memory.vector_store.PGVectorStore") as mock:
        yield mock

@pytest.fixture
def mock_sqlalchemy_create_engine():
    with patch("src.core.memory.vector_store.create_engine") as mock:
        yield mock

def test_vector_memory_self_healing_success(
    mock_embedding_provider,
    mock_pg_engine,
    mock_pg_vector_store,
    mock_sqlalchemy_create_engine
):
    """
    Testa se o mecanismo de auto-cura é acionado quando o erro de schema específico ocorre.
    """
    # Configura o erro na primeira chamada e sucesso na segunda
    error_msg = "Id column, langchain_id, does not exist"
    mock_pg_vector_store.create_sync.side_effect = [Exception(error_msg), MagicMock()]

    # Mock do engine SQLAlchemy para o drop table
    mock_sa_engine = MagicMock()
    mock_sqlalchemy_create_engine.return_value = mock_sa_engine
    mock_connection = MagicMock()
    mock_sa_engine.connect.return_value.__enter__.return_value = mock_connection

    # Executa a inicialização
    vm = VectorMemory()

    # Verifica se create_sync foi chamado duas vezes
    assert mock_pg_vector_store.create_sync.call_count == 2

    # Verifica se o DROP TABLE foi executado
    mock_connection.execute.assert_called()
    # Verifica se o texto do comando contém DROP TABLE e o nome da coleção
    call_args = mock_connection.execute.call_args[0][0]
    assert "DROP TABLE IF EXISTS" in str(call_args)
    assert settings.PGVECTOR_COLLECTION_NAME in str(call_args)

    # Verifica se o commit foi chamado
    mock_connection.commit.assert_called_once()

def test_vector_memory_other_error_propagates(
    mock_embedding_provider,
    mock_pg_engine,
    mock_pg_vector_store,
    mock_sqlalchemy_create_engine
):
    """
    Testa se outros erros (não relacionados ao schema) são propagados sem tentar auto-cura.
    """
    mock_pg_vector_store.create_sync.side_effect = Exception("Connection failed")

    with pytest.raises(Exception) as excinfo:
        VectorMemory()

    assert "Connection failed" in str(excinfo.value)
    # Verifica que chamou apenas uma vez
    assert mock_pg_vector_store.create_sync.call_count == 1
