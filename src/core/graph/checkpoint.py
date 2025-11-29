import os
from langgraph.checkpoint.postgres import PostgresSaver

# Variável global para armazenar a instância do checkpointer (padrão singleton)
_checkpointer = None

def get_checkpointer():
    """
    Retorna uma instância singleton do PostgresSaver para persistência do grafo.
    """
    global _checkpointer
    if _checkpointer is None:
        connection_string = os.getenv("POSTGRES_URL")
        if not connection_string:
            raise ValueError("A variável de ambiente POSTGRES_URL não está definida para o checkpointer.")

        # O PostgresSaver lida com a criação da tabela `checkpoints` automaticamente
        _checkpointer = PostgresSaver.from_conn_string(connection_string)

    return _checkpointer
