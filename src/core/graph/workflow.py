from langgraph.graph import StateGraph, END
from src.core.graph.state import AgentState
from src.agents.tech_lead.agent import TechLeadAgent
from src.agents.fullstack.agent import FullstackAgent
from src.agents.reviewer.agent import CodeReviewAgent
from src.core.models import TaskStatus, DevelopmentStep, DevelopmentPlan, AgentRole, Verdict
from src.tools.core_tools import read_file # Importa a ferramenta de leitura
from typing import Optional
import uuid

# --- NODES ---

def node_planner(state: AgentState) -> dict:
    project_path = state.get("project_path", "./workspace")
    if state.get("plan") and state["plan"].steps:
        return {"current_step_index": 0, "retry_count": 0, "current_step": None}
    original_request = "Auto Task"
    if state.get("plan") and state["plan"].original_request:
        original_request = state["plan"].original_request
    tech_lead = TechLeadAgent(workspace_path=project_path)
    plan = tech_lead.create_development_plan(project_requirements=original_request, code_language="python")
    plan.project_path = project_path
    return {"plan": plan, "current_step_index": 0, "retry_count": 0, "current_step": None}


def node_executor(state: AgentState) -> dict:
    plan = state["plan"]
    idx = state["current_step_index"]
    if idx >= len(plan.steps): return {}

    step = plan.steps[idx]
    project_path = state["project_path"]
    step.status = TaskStatus.IN_PROGRESS

    fullstack = FullstackAgent(workspace_path=project_path)

    # O `execute_step` agora retorna o passo atualizado e os arquivos modificados
    result_step, modified_files = fullstack.execute_step(step)

    plan.steps[idx] = result_step
    return {"plan": plan, "current_step": result_step, "modified_files": modified_files}


def node_reviewer(state: AgentState) -> dict:
    step = state["current_step"]
    modified_files = state.get("modified_files", [])

    if not modified_files:
        # Se nenhum arquivo foi modificado, não há o que revisar.
        # Isso pode ser um PASS ou um FAIL dependendo da tarefa.
        # Por segurança, vamos pedir ao revisor para avaliar a situação.
        code_context = "Nenhum arquivo foi modificado pelo desenvolvedor."
    else:
        code_context = ""
        for filename in modified_files:
            try:
                # Usa a ferramenta para ler o arquivo
                # Note: read_file is a Tool/function, need to invoke it or call it.
                # In core_tools.py it is decorated with @tool.
                # If we imported the function directly (decorated), we can call invoke or run.
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

    # Armazena o veredito estruturado no estado
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
