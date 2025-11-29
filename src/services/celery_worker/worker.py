from celery import Celery
from src.core.graph.workflow import create_dev_graph
from src.core.graph.checkpoint import get_checkpointer
from src.core.models import DevelopmentPlan
import uuid
import os
from dotenv import load_dotenv

# --- LÓGICA DE CARREGAMENTO ROBUSTA ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"AVISO: Arquivo .env não encontrado em {dotenv_path}")
# --- FIM DA LÓGICA ROBUSTA ---

# --- LEITURA EXPLÍCITA DAS CONFIGURAÇÕES ---
redis_host = os.getenv('REDIS_HOST', 'localhost')
postgres_url = os.getenv('POSTGRES_URL') # Lê a URL do Postgres aqui
redis_url = f"redis://{redis_host}:6379/0"
# --- FIM DA LEITURA EXPLÍCITA ---

app = Celery('dev_agent_tasks', broker=redis_url, backend=redis_url)

@app.task(name="run_graph_task")
def run_graph_task(plan_dict: dict):
    """
    Executa o grafo de desenvolvimento de forma assíncrona com persistência.
    """
    # Passa a URL do Postgres explicitamente para evitar problemas de escopo/ambiente
    checkpointer = get_checkpointer(connection_string=postgres_url)
    graph = create_dev_graph(checkpointer=checkpointer)

    plan = DevelopmentPlan(**plan_dict)

    initial_state = {
        "plan": plan,
        "project_path": plan.project_path
    }

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    graph.invoke(initial_state, config=config)

    return thread_id
