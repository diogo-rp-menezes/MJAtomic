from src.core.graph.workflow import create_dev_graph_with_checkpoint
from src.models import DevelopmentPlan, Step, get_engine
from src.models.enums import StepStatus
from .worker import celery_app
from sqlalchemy.orm import sessionmaker

def sync_state_to_db(plan_id: int, graph_state: dict):
    """
    Synchronizes the state of the LangGraph to the relational database.
    """
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    plan = session.query(DevelopmentPlan).filter(DevelopmentPlan.id == plan_id).one_or_none()
    if not plan:
        # Create plan and steps if they don't exist
        plan = DevelopmentPlan(id=plan_id, project_name=graph_state.get("project_name", "Unknown"))
        session.add(plan)
        
        steps_data = graph_state.get("plan", {}).get("steps", [])
        for i, step_data in enumerate(steps_data):
            step = Step(
                plan_id=plan_id,
                description=step_data["step"],
                status=StepStatus.PENDING,
                agent_role="FULLSTACK" # Simplified
            )
            session.add(step)
    
    # Update step status
    current_step_index = graph_state.get("current_step_index", 0)
    step_to_update = session.query(Step).filter(Step.plan_id == plan_id).offset(current_step_index).first()
    if step_to_update:
        # Here you would have more complex logic to map graph state to DB StepStatus
        step_to_update.status = StepStatus.IN_PROGRESS
        
    session.commit()
    session.close()


@celery_app.task(name="run_agent_graph")
def run_agent_graph(plan_id: int, project_name: str):
    """
    Celery task to run the agent development graph.
    """
    app = create_dev_graph_with_checkpoint()
    config = {"configurable": {"thread_id": f"plan-{plan_id}"}}
    
    initial_state = {"project_name": project_name}
    
    for state in app.stream(initial_state, config=config):
        # Sync state to DB after each step
        sync_state_to_db(plan_id, state)
        
    return {"plan_id": plan_id, "status": "completed"}


@celery_app.task(name="resume_agent_graph")
def resume_agent_graph(plan_id: int, feedback: dict):
    """
    Celery task to resume a paused agent graph.
    """
    app = create_dev_graph_with_checkpoint()
    config = {"configurable": {"thread_id": f"plan-{plan_id}"}}
    
    # The `invoke` call with the same thread_id will resume from the last checkpoint
    app.invoke({"human_feedback": feedback}, config=config)
    
    return {"plan_id": plan_id, "status": "resumed"}
