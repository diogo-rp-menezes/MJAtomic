from langgraph.graph import StateGraph, END
from src.core.graph.state import AgentState
from src.agents.tech_lead.agent import TechLeadAgent
from src.agents.fullstack.agent import FullstackAgent
from src.agents.reviewer.agent import CodeReviewAgent
from src.core.models import TaskStatus, Step, DevelopmentPlan, AgentRole
from typing import Optional
import uuid

def node_planner(state: AgentState) -> AgentState:
    project_path = state.get("project_path", "./workspace")
    if state.get("plan") and state["plan"].steps:
        return {"current_step_index": 0, "retry_count": 0}
    original_request = "Auto Task"
    if state.get("plan") and state["plan"].original_request:
        original_request = state["plan"].original_request
    tech_lead = TechLeadAgent(workspace_path=project_path)
    plan = tech_lead.plan_task(original_request)
    plan.project_path = project_path
    return {"plan": plan, "current_step_index": 0, "retry_count": 0}

def node_executor(state: AgentState) -> AgentState:
    plan = state["plan"]
    idx = state["current_step_index"]
    if idx >= len(plan.steps): return {}
    step = plan.steps[idx]
    project_path = state["project_path"]
    step.status = TaskStatus.IN_PROGRESS
    fullstack = FullstackAgent(workspace_path=project_path)
    result_step = fullstack.execute_step(step)
    plan.steps[idx] = result_step
    return {"plan": plan, "current_step": result_step}

def node_reviewer(state: AgentState) -> AgentState:
    plan = state["plan"]
    idx = state["current_step_index"]
    if idx >= len(plan.steps): return {}
    step = plan.steps[idx]
    project_path = state["project_path"]
    reviewer = CodeReviewAgent(workspace_path=project_path)
    reviewed_step = reviewer.review_step(step)
    if "VERDICT: PASS" in (reviewed_step.logs or ""):
        reviewed_step.status = TaskStatus.COMPLETED
    else:
        reviewed_step.status = TaskStatus.FAILED
    plan.steps[idx] = reviewed_step
    return {"plan": plan, "current_step": reviewed_step}

def node_retry_handler(state: AgentState) -> AgentState:
    return {"retry_count": state["retry_count"] + 1}

def node_next_step_handler(state: AgentState) -> AgentState:
    return {"current_step_index": state["current_step_index"] + 1, "retry_count": 0, "current_step": None}

def check_review_outcome(state: AgentState) -> str:
    step = state["current_step"]
    retry = state["retry_count"]
    if not step or step.status == TaskStatus.FAILED:
        return "retry" if retry < 2 else "abort"
    return "success"

def check_if_done(state: AgentState) -> str:
    plan = state["plan"]
    idx = state["current_step_index"]
    if idx < len(plan.steps):
        return "continue"
    return "end"

def create_dev_graph(checkpointer=None, interrupt_before: list = None):
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", node_planner)
    workflow.add_node("executor", node_executor)
    workflow.add_node("reviewer", node_reviewer)
    workflow.add_node("retry_handler", node_retry_handler)
    workflow.add_node("next_step_handler", node_next_step_handler)

    workflow.set_entry_point("planner")

    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "reviewer")
    workflow.add_edge("retry_handler", "executor")

    workflow.add_conditional_edges("reviewer", check_review_outcome, {"retry": "retry_handler", "abort": END, "success": "next_step_handler"})
    workflow.add_conditional_edges("next_step_handler", check_if_done, {"continue": "executor", "end": END})

    return workflow.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)

create_dev_graph_with_checkpoint = create_dev_graph
