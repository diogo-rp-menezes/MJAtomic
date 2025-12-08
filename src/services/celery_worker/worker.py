from celery import Celery
from src.core.graph.workflow import create_dev_graph
from src.core.models import DevelopmentPlan
from src.core.graph.checkpoint import get_checkpointer
from src.core.db_bootstrap import bootstrap_database
from src.core.config import settings

# Configuração do Celery
# O broker e o backend são definidos via src/core/config.py
app = Celery(
    'dev_agent_tasks',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    broker_connection_retry_on_startup=True
)

# Garantia adicional: em ambientes onde o worker roda isolado da API,
# assegura a existência da extensão 'vector' e corrige tabelas incompatíveis.
try:
    bootstrap_database()
except Exception:
    # Não impedimos o worker de subir caso a verificação falhe; o erro ficará nos logs.
    pass

# A responsabilidade de criar as tabelas de ORM e LangGraph permanece na API para evitar race conditions.

@app.task(name="run_graph_task")
def run_graph_task(plan_data: dict):
    """
    Executa o grafo de desenvolvimento de forma assíncrona.
    """
    # Lazy load do checkpointer
    checkpointer = get_checkpointer()

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
