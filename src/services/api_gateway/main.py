from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import FileResponse

from src.models import DevelopmentPlan, Step
from src.services.celery_worker.tasks import run_agent_graph

app = FastAPI()

# --- Data Models ---
class PlanRequest(BaseModel):
    project_name: str

class PlanResponse(BaseModel):
    plan_id: int
    project_name: str

class StepResponse(BaseModel):
    step_id: int
    description: str
    status: str

# --- API Endpoints ---

@app.post("/plans", response_model=PlanResponse)
async def create_plan(request: PlanRequest):
    """
    Creates a new development plan and kicks off the agent graph.
    """
    # In a real app, you'd save this to the DB and get an ID
    plan_id = 1  # Dummy ID
    
    # Start the Celery task
    run_agent_graph.delay(plan_id, request.project_name)
    
    return PlanResponse(plan_id=plan_id, project_name=request.project_name)

@app.get("/plans/{plan_id}/status")
async def get_plan_status(plan_id: int):
    """
    Retrieves the status of all steps in a development plan.
    """
    # Dummy data - in a real app, you'd query the DB
    steps_data = [
        {"step_id": 1, "description": "Write tests for login", "status": "COMPLETED"},
        {"step_id": 2, "description": "Implement login logic", "status": "IN_PROGRESS"},
    ]
    return {"plan_id": plan_id, "steps": steps_data}

@app.post("/resume/{plan_id}")
async def resume_plan(plan_id: int, feedback: dict):
    """
    Resumes a paused graph, potentially with human feedback.
    """
    # This would interact with the graph's checkpoint to resume execution
    return {"message": f"Plan {plan_id} resumed with feedback."}


# --- Static Files for Dashboard ---

# Mount the static directory
app.mount("/dashboard", StaticFiles(directory="src/services/api_gateway/static"), name="dashboard")

@app.get("/")
async def read_root():
    """
    Redirects to the dashboard.
    """
    return FileResponse("src/services/api_gateway/static/index.html")
