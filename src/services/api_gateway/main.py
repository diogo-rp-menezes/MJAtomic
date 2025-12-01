from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from src.core.models import TaskRequest, DevelopmentPlan
from src.services.celery_worker.worker import run_graph_task
from src.core.graph.checkpoint import get_checkpointer
from typing import Dict, Any

app = FastAPI(title="DevAgentAtomic API")

# --- PRESERVAR ESTA SEÇÃO ---
# Monta o diretório 'dashboard' para servir a UI estática
# Ajustado para src/frontend onde os arquivos realmente existem
app.mount("/dashboard", StaticFiles(directory="src/frontend", html=True), name="dashboard")
# --- FIM DA SEÇÃO A PRESERVAR ---

@app.post("/tasks/create", response_model=Dict[str, str], status_code=202)
async def create_development_task(request: TaskRequest):
    """
    Recebe uma nova tarefa de desenvolvimento e a inicia em segundo plano.
    """
    initial_plan = DevelopmentPlan(
        original_request=request.description,
        project_path=request.project_path or "./workspace"
    )

    # A task do Celery precisa de um dicionário serializável
    task_result = run_graph_task.delay(initial_plan.model_dump())

    return {"message": "Tarefa de desenvolvimento aceita.", "task_id": task_result.id}

@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Consulta o estado atual de uma tarefa de desenvolvimento em andamento.
    (NOTA: Implementação simplificada para este sprint)
    """
    try:
        checkpointer = get_checkpointer()
        # A implementação real é mais complexa, mas a base está aqui.
        return JSONResponse(
            status_code=200,
            content={
                "message": "Funcionalidade de status em desenvolvimento.",
                "task_id": task_id,
                "detail": "A persistência está implementada via LangGraph Checkpointer."
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar o checkpointer: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "DevAgentAtomic API está online."}
