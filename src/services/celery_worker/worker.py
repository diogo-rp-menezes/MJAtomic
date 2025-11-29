from celery import Celery
from src.core.graph.workflow import create_dev_graph
from src.core.graph.checkpoint import get_checkpointer
from src.core.models import DevelopmentPlan
import uuid
import os

# Configuração do Celery
# Idealmente, isso viria de uma configuração central, mas por enquanto está bom aqui.
# Mantendo fallback para REDIS_HOST se definido, ou localhost.
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_url = f"redis://{redis_host}:6379/0"

app = Celery('dev_agent_tasks', broker=redis_url, backend=redis_url)

@app.task(name="run_graph_task")
def run_graph_task(plan_dict: dict):
    """
    Executa o grafo de desenvolvimento de forma assíncrona com persistência.
    """
    checkpointer = get_checkpointer()
    graph = create_dev_graph(checkpointer=checkpointer)

    # Converte o dicionário de volta para um objeto Pydantic
    plan = DevelopmentPlan(**plan_dict)

    # IMPORTANTE: Adicionar project_path ao estado inicial, pois node_executor depende dele.
    initial_state = {
        "plan": plan,
        "project_path": plan.project_path
    }

    # Gera um ID de thread único para esta execução
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Invoca o grafo. O checkpointer salvará o estado automaticamente.
    # Não precisamos esperar o resultado aqui, pois a tarefa é assíncrona.
    graph.invoke(initial_state, config=config)

    # Retorna o ID da thread para que o status possa ser consultado
    return thread_id
