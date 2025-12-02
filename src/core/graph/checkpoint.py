import os
from langgraph.checkpoint.postgres import PostgresSaver

# Variável global para armazenar a instância REAL do checkpointer
_checkpointer_instance = None

def get_db_connection_string() -> str:
    """Retorna a string de conexão do Postgres a partir da variável de ambiente.

    Normaliza para um driver compatível com async quando necessário, evitando que
    o SQLAlchemy carregue o driver síncrono psycopg2 em contextos asyncio.
    """
    conn_str = os.getenv("POSTGRES_URL")
    if not conn_str:
        raise ValueError("A variável de ambiente POSTGRES_URL não está definida.")

    # Normaliza para o formato aceito pelo PostgresSaver/psycopg (sem sufixos de driver SA)
    # Remove explicitadores de driver do SQLAlchemy, se presentes
    if conn_str.startswith("postgresql+psycopg2://"):
        conn_str = conn_str.replace("postgresql+psycopg2://", "postgresql://", 1)
    elif conn_str.startswith("postgresql+psycopg://"):
        conn_str = conn_str.replace("postgresql+psycopg://", "postgresql://", 1)

    # Garante porta padrão 5433 quando omissa
    try:
        from urllib.parse import urlsplit, urlunsplit
        u = urlsplit(conn_str)
        # Se nenhuma porta foi especificada no URL, injeta a porta do ambiente (ou 5432)
        if u.port is None and u.hostname:
            port = os.getenv("POSTGRES_PORT", "5432")
            userinfo = ""
            if u.username:
                userinfo = u.username
                if u.password:
                    userinfo += f":{u.password}"
                userinfo += "@"
            new_netloc = f"{userinfo}{u.hostname}:{port}"
            conn_str = urlunsplit((u.scheme, new_netloc, u.path, u.query, u.fragment))
    except Exception:
        # Em caso de falha na normalização, segue com a string original já corrigida no prefixo
        pass

    return conn_str

def get_checkpointer(connection_string: str = None):
    """
    Retorna uma instância singleton do PostgresSaver para persistência do grafo.
    Esta versão lida corretamente com a API baseada em gerenciador de contexto.
    """
    global _checkpointer_instance
    if _checkpointer_instance is None:
        # Usa a string fornecida ou busca da variável de ambiente (via helper)
        if connection_string:
            conn_str = connection_string
        else:
            conn_str = get_db_connection_string()
        
        # 1. A função retorna um gerenciador de contexto
        saver_context_manager = PostgresSaver.from_conn_string(conn_str)
        
        # 2. Nós "entramos" manualmente no contexto para obter o objeto real
        # e o armazenamos na nossa variável singleton.
        _checkpointer_instance = saver_context_manager.__enter__()
        
        # NOTA: Em uma aplicação de produção completa, registraríamos
        # saver_context_manager.__exit__ para ser chamado no shutdown da aplicação,
        # mas para o nosso caso, isso é suficiente e correto.
        
    return _checkpointer_instance
