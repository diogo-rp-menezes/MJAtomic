import os
import warnings
from celery import Celery
from celery.exceptions import SecurityWarning
from src.core.graph.workflow import create_dev_graph
from langgraph.checkpoint.postgres import PostgresSaver
from src.core.graph.checkpoint import get_db_connection_string
from src.core.models import DevelopmentPlan
import uuid
from dotenv import load_dotenv

# Configura C_FORCE_ROOT antes de qualquer outra coisa para garantir
os.environ.setdefault('C_FORCE_ROOT', 'true')
# Ignora o aviso de segurança específico do Celery sobre execução como root
warnings.filterwarnings("ignore", category=SecurityWarning)

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
redis_url = f"redis://{redis_host}:6379/0"
# --- FIM DA LEITURA EXPLÍCITA ---

# Garante que as tabelas do checkpointer existam
try:
    conn_str = get_db_connection_string()
    with PostgresSaver.from_conn_string(conn_str) as checkpointer:
        checkpointer.setup()
except Exception as e:
    print(f"AVISO: Não foi possível inicializar as tabelas do checkpointer no startup do worker: {e}")

app = Celery('dev_agent_tasks', broker=redis_url, backend=redis_url)

@app.task(name="run_graph_task")
def run_graph_task(plan_dict: dict):
    """
    Executa o grafo de desenvolvimento de forma assíncrona com persistência.
    """
    postgres_url = get_db_connection_string()

    # Usa o PostgresSaver como um context manager para garantir que a conexão
    # seja aberta e fechada corretamente para cada tarefa.
    with PostgresSaver.from_conn_string(postgres_url) as checkpointer:
        checkpointer.setup() # Garante que a tabela existe (idempotente)
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
