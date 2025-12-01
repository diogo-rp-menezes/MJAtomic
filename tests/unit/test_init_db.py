from unittest.mock import patch, MagicMock
from src.core.database import init_db

@patch("src.core.database.Base.metadata.create_all")
@patch("src.core.graph.checkpoint.get_db_connection_string")  # Patch where it's defined or imported from
@patch("langgraph.checkpoint.postgres.PostgresSaver")         # Patch the original class
def test_init_db(mock_postgres_saver, mock_get_conn_str, mock_create_all):
    # Setup mocks
    mock_get_conn_str.return_value = "postgresql://user:pass@localhost:5432/db"
    mock_saver_instance = MagicMock()

    # Mock the context manager behavior of from_conn_string
    # from_conn_string returns a context manager, so __enter__ returns the saver instance
    mock_postgres_saver.from_conn_string.return_value.__enter__.return_value = mock_saver_instance

    # Run init_db
    init_db()

    # Verify calls
    mock_create_all.assert_called_once()
    mock_get_conn_str.assert_called_once()
    mock_postgres_saver.from_conn_string.assert_called_once_with("postgresql://user:pass@localhost:5432/db")
    mock_saver_instance.setup.assert_called_once()
