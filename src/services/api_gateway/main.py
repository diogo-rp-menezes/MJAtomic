import traceback
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from src.core.models import TaskRequest, DevelopmentPlan as PydanticPlan, TaskStatus, Step as PydanticStep, ProjectInitRequest
from src.agents.tech_lead.agent import TechLeadAgent
from src.agents.architect.agent import ArchitectAgent
from src.services.celery_worker.worker import run_agent_graph, resume_agent_graph
from src.core.database import get_db, init_db
from src.core.repositories import TaskRepository
from pydantic import BaseModel
import json
import os

app = FastAPI(title="DevAgentAtomic API", version="0.5.0 (LangGraph)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResumeRequest(BaseModel):
    user_input: str

@app.on_event("startup")
def on_startup():
    init_db()

os.makedirs("src/frontend", exist_ok=True)
# app.mount("/dashboard", StaticFiles(directory="src/frontend", html=True), name="dashboard") # Commented out if directory doesn't exist yet in runtime, but we created it.

@app.post("/init-project")
async def init_project(request: ProjectInitRequest):
    try:
        if request.root_path:
            final_path = os.path.abspath(request.root_path)
        else:
            safe_name = request.project_name.replace(" ", "_").lower()
            final_path = os.path.abspath(f"./workspace/{safe_name}")

        os.makedirs(final_path, exist_ok=True)

        architect = ArchitectAgent(workspace_path=final_path)
        result = architect.init_project(request.project_name, request.description, request.stack_preference)

        return {"status": "success", "message": result, "path": final_path}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/audit", response_model=PydanticPlan)
async def audit_project(request: TaskRequest, db: Session = Depends(get_db)):
    try:
        final_path = os.path.abspath(request.project_path) if request.project_path else "./workspace"

        # llm = LLMProvider(profile="smart") # Not used here directly, inside agent
        # fio = FileIOTool(root_path=final_path) # Inside agent

        tech_lead = TechLeadAgent(workspace_path=final_path)

        plan_pydantic = tech_lead.audit_and_plan(request.description)
        plan_pydantic.project_path = final_path

        repo = TaskRepository(db)
        db_plan = repo.create_plan(plan_pydantic)
        return _db_to_pydantic_plan(db_plan)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute/{plan_id}")
async def execute_plan(plan_id: str, db: Session = Depends(get_db)):
    print(f"🚀 [API] Executing Plan: {plan_id}")
    try:
        repo = TaskRepository(db)
        db_plan = repo.get_plan(plan_id)
        if not db_plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        plan_pydantic = _db_to_pydantic_plan(db_plan)

        print(f"🔥 [API] Sending plan to LangGraph worker...")
        task = run_agent_graph.delay(plan_pydantic.model_dump_json(), db_plan.project_path, thread_id=plan_id)
        print(f"✅ [API] Task sent! ID: {task.id}")

        return {"status": "started", "task_id": task.id}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resume/{plan_id}")
async def resume_execution(plan_id: str, request: ResumeRequest):
    try:
        print(f"⏯️ [API] Resuming Plan: {plan_id} with input: {request.user_input}")
        task = resume_agent_graph.delay(thread_id=plan_id, user_input=request.user_input)
        return {"status": "resumed", "task_id": task.id}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks", response_model=List[PydanticPlan])
async def list_tasks(db: Session = Depends(get_db)):
    repo = TaskRepository(db)
    db_plans = repo.get_all_plans()
    return [_db_to_pydantic_plan(p) for p in db_plans]

@app.get("/tasks/{plan_id}", response_model=PydanticPlan)
async def get_task(plan_id: str, db: Session = Depends(get_db)):
    repo = TaskRepository(db)
    db_plan = repo.get_plan(plan_id)
    if not db_plan: raise HTTPException(404)
    return _db_to_pydantic_plan(db_plan)

def _db_to_pydantic_plan(db_plan) -> PydanticPlan:
    return PydanticPlan(
        id=db_plan.id,
        original_request=db_plan.original_request,
        project_path=getattr(db_plan, 'project_path', './workspace'),
        created_at=db_plan.created_at,
        steps=[PydanticStep(id=s.id, description=s.description, role=s.role, status=s.status, result=s.result or "", logs=s.logs or "") for s in db_plan.steps]
    )
