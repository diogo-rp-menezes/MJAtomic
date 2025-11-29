import sys
import os
import json
from celery import Celery
from src.core.graph.workflow import create_dev_graph
from src.core.graph.checkpoint import PostgresSaver
from src.core.models import DevelopmentPlan, DevelopmentStep
from src.core.database import SessionLocal
from src.core.repositories import TaskRepository
from src.core.logger import logger

sys.path.insert(0, os.getcwd())

redis_url = f"redis://{os.getenv('REDIS_HOST', 'localhost')}:6379/0"
celery_app = Celery("dev_agent_tasks", broker=redis_url, backend=redis_url)

def sync_state_to_db(plan: DevelopmentPlan):
    try:
        db = SessionLocal()
        repo = TaskRepository(db)
        for step in plan.steps:
            if step.id:
                repo.update_step(step.id, step.status, step.result, step.logs)
        db.close()
    except Exception as e:
        logger.error(f"Failed to sync state to DB: {e}")

@celery_app.task(bind=True)
def run_agent_graph(self, plan_json: str, project_path: str, thread_id: str = None):
    logger.info(f"🚀 START GRAPH EXECUTION | Project: {project_path} | Thread: {thread_id}")

    try:
        plan_dict = json.loads(plan_json)
        plan = DevelopmentPlan(**plan_dict)

        checkpointer = PostgresSaver()
        interrupt_before = ["executor"]
        app = create_dev_graph(checkpointer=checkpointer, interrupt_before=interrupt_before)

        initial_state = {
            "plan": plan,
            "current_step_index": 0,
            "retry_count": 0,
            "project_path": project_path
        }

        config = {"configurable": {"thread_id": thread_id or plan.id or "default_thread"}}

        for event in app.stream(initial_state, config=config):
            for node, state_update in event.items():
                logger.info(f"🔄 Graph Node Completed: {node}")
                if "plan" in state_update:
                    sync_state_to_db(state_update["plan"])

        return "Graph Execution Completed"

    except Exception as e:
        logger.exception("💥 CRITICAL GRAPH ERROR")
        return f"Error: {str(e)}"

@celery_app.task(bind=True)
def resume_agent_graph(self, thread_id: str, user_input: str):
    logger.info(f"⏯️ RESUME GRAPH | Thread: {thread_id} | Input: {user_input}")
    try:
        checkpointer = PostgresSaver()
        app = create_dev_graph(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": thread_id}}

        for event in app.stream(None, config=config):
             for node, state_update in event.items():
                logger.info(f"🔄 Graph Node Resumed: {node}")
                if "plan" in state_update:
                    sync_state_to_db(state_update["plan"])

        return "Graph Resumed"
    except Exception as e:
        logger.exception("💥 RESUME ERROR")
        return f"Error: {str(e)}"
