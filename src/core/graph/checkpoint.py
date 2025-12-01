import os
from langgraph.checkpoint.postgres import PostgresSaver

# Variável global para armazenar a instância REAL do checkpointer
_checkpointer_instance = None

def get_db_connection_string() -> str:
    """
    Retorna a string de conexão do PostgreSQL.
    Prioriza a variável de ambiente POSTGRES_URL, mas faz fallback para construção
    baseada em variáveis individuais (usada pelo database.py e docker-compose).
    """
    conn_str = os.getenv("POSTGRES_URL")
    if conn_str:
        return conn_str

    # Fallback para construção manual
    user = os.getenv("POSTGRES_USER", "devagent")
    password = os.getenv("POSTGRES_PASSWORD", "atomicpass")
    host = os.getenv("POSTGRES_HOST", "db")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "devagent_db")

    # LangGraph PostgresSaver usa psycopg v3 (conninfo ou URI)
    # Formato URI padrão: postgresql://user:password@host:port/dbname
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

def get_checkpointer(connection_string: str = None):
    """
    Retorna uma instância singleton do PostgresSaver para persistência do grafo.
    Esta versão lida corretamente com a API baseada em gerenciador de contexto.
    """
    global _checkpointer_instance
    if _checkpointer_instance is None:
        conn_str = connection_string or get_db_connection_string()
        
        if not conn_str:
            raise ValueError("String de conexão do Postgres não foi fornecida e a variável de ambiente POSTGRES_URL não está definida.")
        
        # 1. A função retorna um gerenciador de contexto
        saver_context_manager = PostgresSaver.from_conn_string(conn_str)
        
        # 2. Nós "entramos" manualmente no contexto para obter o objeto real
        # e o armazenamos na nossa variável singleton.
        _checkpointer_instance = saver_context_manager.__enter__()
        
        # NOTA: Em uma aplicação de produção completa, registraríamos
        # saver_context_manager.__exit__ para ser chamado no shutdown da aplicação,
        # mas para o nosso caso, isso é suficiente e correto.
        
    return _checkpointer_instance
