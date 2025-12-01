from langgraph.graph import StateGraph, END
from src.core.graph.state import AgentState
from src.agents.tech_lead.agent import TechLeadAgent
from src.agents.fullstack.agent import FullstackAgent
from src.agents.reviewer.agent import CodeReviewAgent
from src.core.models import TaskStatus, DevelopmentStep, DevelopmentPlan, AgentRole, Verdict, CodeReviewVerdict
from src.tools.core_tools import read_file
from src.core.database import SessionLocal
from src.core.repositories import TaskRepository
from typing import Optional
import uuid

# --- NODES ---

def node_planner(state: AgentState) -> dict:
    project_path = state.get("project_path", "./workspace")
    if state.get("plan") and state["plan"].steps:
        return {"current_step_index": 0, "retry_count": 0, "current_step": None, "review_verdict": None}
    original_request = "Auto Task"
    existing_id = None
    if state.get("plan"):
        if state["plan"].original_request:
            original_request = state["plan"].original_request
        if state["plan"].id:
            existing_id = state["plan"].id

    tech_lead = TechLeadAgent(workspace_path=project_path)
    plan = tech_lead.create_development_plan(project_requirements=original_request, code_language="python")
    plan.project_path = project_path

    # Preserva o ID do plano e persiste os passos gerados
    if existing_id:
        plan.id = existing_id
        try:
            with SessionLocal() as db:
                repo = TaskRepository(db)
                repo.add_steps(plan.id, plan.steps)
        except Exception as e:
            print(f"Erro ao persistir passos do plano: {e}")

    return {
        "plan": plan,
        "project_path": plan.project_path,
        "current_step_index": 0,
        "retry_count": 0,
        "current_step": None,
        "review_verdict": None,
    }


def node_executor(state: AgentState) -> dict:
    plan = state["plan"]
    idx = state["current_step_index"]
    if idx >= len(plan.steps): return {}

    step = plan.steps[idx]
    project_path = state["project_path"]

    # Atualiza status para IN_PROGRESS no DB
    step.status = TaskStatus.IN_PROGRESS
    try:
        with SessionLocal() as db:
            repo = TaskRepository(db)
            repo.update_step(step.id, status=step.status)
    except Exception as e:
        print(f"Erro ao atualizar status do passo para IN_PROGRESS: {e}")

    fullstack = FullstackAgent(workspace_path=project_path)

    # --- LÓGICA DE SELF-HEALING INTELIGENTE ---
    review = state.get("review_verdict")
    task_input = f"Complete a seguinte tarefa de desenvolvimento: {step.description}"

    if review and review.verdict == Verdict.FAIL:
        task_input = (
            f"Sua tentativa anterior falhou na revisão de código. "
            f"Justificativa do revisor: '{review.justification}'.\n\n"
            f"Por favor, analise este feedback, corrija o problema e complete a tarefa original: {step.description}"
        )
    # --- FIM DA LÓGICA ---

    # O `execute_step` agora recebe o input dinâmico
    result_step, modified_files = fullstack.execute_step(step, task_input)

    # Persiste o resultado no DB
    try:
        with SessionLocal() as db:
            repo = TaskRepository(db)
            repo.update_step(result_step.id, status=result_step.status, result=result_step.result, logs=result_step.logs)
    except Exception as e:
        print(f"Erro ao atualizar resultado do passo: {e}")

    plan.steps[idx] = result_step
    # Limpa o veredito antigo para o próximo ciclo
    return {"plan": plan, "current_step": result_step, "modified_files": modified_files, "review_verdict": None}


def node_reviewer(state: AgentState) -> dict:
    step = state.get("current_step")

    if not step:
        return {"review_verdict": CodeReviewVerdict(verdict=Verdict.FAIL, justification="Internal Error: Step not found in state")}

    modified_files = state.get("modified_files", [])
    
    if not modified_files:
        code_context = "Nenhum arquivo foi modificado pelo desenvolvedor."
    else:
        code_context = ""
        for filename in modified_files:
            try:
                content = read_file.invoke(filename)
                code_context += f"--- {filename} ---\n{content}\n\n"
            except Exception as e:
                code_context += f"--- {filename} ---\nErro ao ler o arquivo: {e}\n\n"

    reviewer = CodeReviewAgent()
    verdict = reviewer.review_code(
        task_description=step.description,
        code_context=code_context,
        execution_logs=step.logs or ""
    )
    
    return {"review_verdict": verdict}


def node_retry_handler(state: AgentState) -> dict:
    return {"retry_count": state["retry_count"] + 1}


def node_next_step_handler(state: AgentState) -> dict:
    return {"current_step_index": state["current_step_index"] + 1, "retry_count": 0, "current_step": None}


# --- EDGES ---

def check_review_outcome(state: AgentState) -> str:
    """Verifica o veredito da revisão de forma robusta usando o Enum."""
    verdict = state.get("review_verdict")
    retry_count = state.get("retry_count", 0)
    
    if verdict and verdict.verdict == Verdict.PASS:
        return "success"
    
    if retry_count < 2:
        return "retry"
    
    return "abort"


def check_if_done(state: AgentState) -> str:
    plan = state["plan"]
    idx = state["current_step_index"]
    if idx < len(plan.steps):
        return "continue"
    return "end"


# --- GRAPH ---

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
