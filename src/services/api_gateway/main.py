from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
import os
import shutil

from src.core.models import TaskRequest, DevelopmentPlan, ProjectInitRequest, DevelopmentStep
from src.services.celery_worker.worker import run_graph_task
from src.core.graph.checkpoint import get_checkpointer
from src.core.database import get_db, init_db
from src.core.repositories import TaskRepository
from src.services.api_gateway.dtos import AuditRequest, ResumeRequest
from src.core.config import settings

# Tools & Agents
from src.core.llm.provider import LLMProvider
from src.tools.file_io import FileIOTool
from src.tools.architect.project_builder import StructureBuilderTool
from src.agents.tech_lead.agent import TechLeadAgent

logger = logging.getLogger("api_gateway")

app = FastAPI(title="DevAgentAtomic API")

@app.on_event("startup")
def startup_event():
    init_db()

# Monta o diretório 'dashboard' para servir a UI estática
static_dir = settings.STATIC_DIR
if not os.path.exists(static_dir):
    # Fallback for local development if not in Docker or before build
    static_dir = settings.STATIC_DIR_FALLBACK

if not os.path.exists(static_dir):
    # Ensure directory exists to prevent Starlette RuntimeError during tests
    os.makedirs(static_dir, exist_ok=True)
    # Create a dummy index.html if it doesn't exist, just for basic serving tests
    with open(os.path.join(static_dir, "index.html"), "w") as f:
        f.write("<html><body>Dashboard Placeholder</body></html>")

app.mount("/dashboard", StaticFiles(directory=static_dir, html=True), name="dashboard")

@app.get("/tasks", response_model=List[DevelopmentPlan])
def get_tasks(db: Session = Depends(get_db)):
    """
    Retorna a lista de planos de desenvolvimento (tarefas).
    """
    repo = TaskRepository(db)
    db_plans = repo.get_all_plans()

    # Conversão manual de ORM para Pydantic para garantir compatibilidade
    plans = []
    for p in db_plans:
        steps = [
            DevelopmentStep(
                id=s.id,
                description=s.description,
                role=s.role,
                status=s.status,
                result=s.result or "",
                logs=s.logs or ""
            ) for s in p.steps
        ]
        plans.append(DevelopmentPlan(
            id=p.id,
            original_request=p.original_request,
            project_path=p.project_path,
            created_at=p.created_at,
            steps=steps
        ))
    return plans

@app.post("/tasks/create", response_model=Dict[str, str], status_code=202)
async def create_development_task(request: TaskRequest, db: Session = Depends(get_db)):
    """
    Recebe uma nova tarefa de desenvolvimento e a inicia em segundo plano.
    (Compatibilidade com endpoint original)
    """
    initial_plan = DevelopmentPlan(
        original_request=request.description,
        project_path=request.project_path or settings.DEFAULT_PROJECT_PATH
    )

    # Salva estado inicial no banco
    repo = TaskRepository(db)
    db_plan = repo.create_plan(initial_plan)

    # Atualiza o ID no objeto Pydantic para passar para o Celery
    initial_plan.id = str(db_plan.id)

    # A task do Celery precisa de um dicionário serializável
    task_result = run_graph_task.delay(initial_plan.model_dump())

    return {"message": "Tarefa de desenvolvimento aceita.", "task_id": str(db_plan.id)}

@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Consulta o estado atual de uma tarefa de desenvolvimento em andamento.
    """
    try:
        # Aqui poderíamos checar o checkpointer, mas o dashboard usa o GET /tasks e
        # consulta o DB via TaskRepository. Este endpoint é mantido para compatibilidade.
        return JSONResponse(
            status_code=200,
            content={
                "message": "Funcionalidade de status em desenvolvimento.",
                "task_id": task_id,
                "detail": "Use GET /tasks para ver o estado atualizado do banco."
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar status: {str(e)}")

@app.post("/audit", response_model=DevelopmentPlan)
def audit_project(request: AuditRequest, db: Session = Depends(get_db)):
    """
    Cria um plano de desenvolvimento (Audit) de forma síncrona usando o TechLeadAgent
    e o salva no banco de dados.
    """
    try:
        # 1. TechLead Logic
        agent = TechLeadAgent(workspace_path=request.project_path)
        plan = agent.create_development_plan(request.description, request.code_language)
        plan.project_path = request.project_path

        # 2. Save to DB
        repo = TaskRepository(db)
        db_plan = repo.create_plan(plan)

        # 3. Retorna o plano salvo com ID gerado
        steps = [
            DevelopmentStep(
                id=s.id,
                description=s.description,
                role=s.role,
                status=s.status,
                result=s.result or "",
                logs=s.logs or ""
            ) for s in db_plan.steps
        ]

        return DevelopmentPlan(
            id=db_plan.id,
            original_request=db_plan.original_request,
            project_path=db_plan.project_path,
            created_at=db_plan.created_at,
            steps=steps
        )
    except Exception as e:
        logger.error(f"Erro no audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/init-project")
async def init_project(request: ProjectInitRequest):
    """
    Reseta o diretório de workspace para um estado limpo.
    """
    workspace_path = request.root_path or settings.DEFAULT_PROJECT_PATH

    try:
        if os.path.exists(workspace_path):
            shutil.rmtree(workspace_path)
        os.makedirs(workspace_path)
        return {"status": "success", "message": f"Workspace em {workspace_path} foi resetado com sucesso.", "path": workspace_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao resetar workspace: {str(e)}")

@app.post("/execute/{task_id}")
def execute_task(task_id: str, db: Session = Depends(get_db)):
    """
    Dispara a execução de um plano existente via Celery.
    """
    repo = TaskRepository(db)
    db_plan = repo.get_plan(task_id)
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Serializa para o formato esperado pelo Celery (DevelopmentPlan dict)
    plan_data = {
        "id": str(db_plan.id),
        "original_request": db_plan.original_request,
        "project_path": db_plan.project_path,
        "steps": [
            {
                "id": s.id,
                "description": s.description,
                "role": s.role,
                "status": s.status,
                "result": s.result,
                "logs": s.logs
            } for s in db_plan.steps
        ]
    }

    # Dispara task assíncrona
    run_graph_task.delay(plan_data)

    return {"status": "started", "task_id": task_id, "message": "Execução iniciada."}

@app.post("/resume/{task_id}")
def resume_task(task_id: str, request: ResumeRequest):
    """
    Endpoint placeholder para retomada de tarefas pausadas (Human-in-the-loop).
    """
    return {"status": "resumed", "message": f"Sinal de retomada enviado para tarefa {task_id} com input: {request.user_input}"}

@app.get("/")
def read_root():
    return {"message": "DevAgentAtomic API está online."}
