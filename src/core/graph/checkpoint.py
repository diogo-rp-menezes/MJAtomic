from langgraph_checkpoint_postgres import PostgresSaver
from src.core.config.settings import settings


def get_checkpoint_saver() -> PostgresSaver:
    """
    Returns an instance of the PostgresSaver.
    """
    return PostgresSaver.from_conn_string(settings.DATABASE_URL)
