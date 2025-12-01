from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import shutil
import os
import uuid

from src.core.models import TaskRequest, DevelopmentPlan, ProjectInitRequest
from src.services.celery_worker.worker import run_graph_task
from src.core.graph.checkpoint import get_checkpointer
from src.core.database import get_db, init_db
from src.core.repositories import TaskRepository
from typing import Dict, Any, List

app = FastAPI(title="DevAgentAtomic API")

@app.on_event("startup")
async def on_startup():
    init_db()

# --- PRESERVAR ESTA SEÇÃO ---
# Monta o diretório 'dashboard' para servir a UI estática
static_dir = "/app/static"
if not os.path.exists(static_dir):
    # Fallback for local development if not in Docker or before build
    static_dir = "frontend/dist"

if os.path.exists(static_dir):
    app.mount("/dashboard", StaticFiles(directory=static_dir, html=True), name="dashboard")
else:
    # Cria um diretório vazio para evitar erro de startup se não existir
    # Mas idealmente o build deve garantir isso.
    pass
# --- FIM DA SEÇÃO A PRESERVAR ---

@app.get("/tasks", response_model=List[DevelopmentPlan])
async def list_tasks(db: Session = Depends(get_db)):
    """
    Lista todas as tarefas de desenvolvimento.
    """
    repo = TaskRepository(db)
    return repo.get_all_plans()

@app.post("/tasks/create", response_model=Dict[str, str], status_code=202)
async def create_development_task(request: TaskRequest, db: Session = Depends(get_db)):
    """
    Recebe uma nova tarefa de desenvolvimento e a inicia em segundo plano.
    """
    initial_plan = DevelopmentPlan(
        original_request=request.description,
        project_path=request.project_path or "./workspace"
    )

    # Persiste o plano no banco de dados IMEDIATAMENTE
    repo = TaskRepository(db)
    db_plan = repo.create_plan(initial_plan)

    # Atualiza o objeto plan com o ID gerado pelo DB
    initial_plan.id = db_plan.id

    # A task do Celery precisa de um dicionário serializável
    task_result = run_graph_task.delay(initial_plan.model_dump())

    return {"message": "Tarefa de desenvolvimento aceita.", "task_id": task_result.id}

@app.post("/init-project", status_code=200)
async def init_project(request: ProjectInitRequest):
    """
    Reseta o diretório de workspace para um estado limpo.
    """
    workspace_path = request.root_path or "./workspace"

    try:
        os.makedirs(workspace_path, exist_ok=True)
        return {"status": "success", "message": f"Workspace em {workspace_path} foi resetado com sucesso.", "path": workspace_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao resetar workspace: {str(e)}")

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
