from celery import Celery
from src.core.graph.workflow import create_dev_graph
from src.core.models import DevelopmentPlan
from langgraph.checkpoint.postgres import PostgresSaver
from src.core.graph.checkpoint import get_db_connection_string
import os

# Configuração do Celery
# O broker e o backend são definidos via variáveis de ambiente ou usam o default do Redis.
redis_host = os.getenv('REDIS_HOST', 'localhost')
app = Celery(
    'dev_agent_tasks',
    broker=f'redis://{redis_host}:6379/0',
    backend=f'redis://{redis_host}:6379/0',
    broker_connection_retry_on_startup=True
)

# A responsabilidade de criar as tabelas foi centralizada no startup da API (main.py)
# para evitar race conditions. O worker apenas usa o checkpointer.
checkpointer = None
postgres_url = get_db_connection_string()
if postgres_url:
    checkpointer = PostgresSaver.from_conn_string(postgres_url)

@app.task(name="run_graph_task")
def run_graph_task(plan_data: dict):
    """
    Executa o grafo de desenvolvimento de forma assíncrona.
    """
    # Recria o objeto Pydantic a partir do dicionário
    initial_plan = DevelopmentPlan.model_validate(plan_data)

    # Configuração para a execução do grafo
    config = {
        "configurable": {
            "thread_id": initial_plan.id,
            "checkpointer": checkpointer,
        }
    }
    initial_state = {
        "plan": initial_plan,
        "project_path": initial_plan.project_path,
    }

    # Cria e executa o grafo
    graph = create_dev_graph()
    final_state = graph.invoke(initial_state, config=config)

    # Retorna o ID da thread para referência futura
    return str(final_state['plan'].id)
