from langgraph.graph import StateGraph, END
from src.core.graph.state import AgentState
from src.agents.tech_lead.agent import TechLeadAgent
from src.agents.fullstack.agent import FullstackAgent
from src.agents.reviewer.agent import CodeReviewAgent
from src.agents.architect.agent import ArchitectAgent
from src.core.models import TaskStatus, DevelopmentStep, DevelopmentPlan, AgentRole, Verdict, CodeReviewVerdict
from src.core.factory import AgentFactory
from src.tools.core_tools import read_file
from src.core.database import SessionLocal
from src.core.repositories import TaskRepository
from typing import Optional
import uuid
import os

# --- NODES ---

def node_architect(state: AgentState) -> dict:
    """
    Nó do Arquiteto (Cloud - Gemini):
    Verifica se o projeto precisa ser inicializado (guidelines.md, README, etc).
    Se sim, gera a documentação inicial e a estrutura base.
    """
    project_path = state.get("project_path", "./workspace")
    plan = state.get("plan")

    # Verifica se já existe documentação base para evitar re-execução desnecessária
    guidelines_path = os.path.join(project_path, ".ai/guidelines.md")
    if os.path.exists(guidelines_path):
        print(f"ℹ️ Projeto em '{project_path}' já parece inicializado. Pulando Arquiteto.")
        return {}

    print(f"🏗️ Iniciando Arquiteto no projeto: {project_path}")

    # Instancia Arquiteto via Factory (garante Provider=Google)
    architect = AgentFactory.create_agent(AgentRole.ARCHITECT, project_path=project_path)

    request_desc = "Novo Projeto"
    if plan and plan.original_request:
        request_desc = plan.original_request

    # Executa a inicialização
    # O Arquiteto gera guidelines, readme, estrutura de pastas e git init
    architect_output = architect.init_project(
        project_name="DevAgent Project",
        description=request_desc
    )

    # Enriquece o request original com o contexto do Arquiteto para o Tech Lead (Local)
    if plan:
        plan.original_request += f"\n\n[CONTEXTO DO ARQUITETO]\n{architect_output}"

    return {"plan": plan}


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

    tech_lead = AgentFactory.create_agent(AgentRole.TECH_LEAD, project_path=project_path)
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

    fullstack = AgentFactory.create_agent(AgentRole.FULLSTACK, project_path=project_path)

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
    logs = step.logs or ""
    
    # [MELHORIA] Detecção de Intenção
    code_context = ""

    if modified_files:
        # Cenário A: Tem arquivos
        for filename in modified_files:
            try:
                content = read_file.invoke(filename)
                code_context += f"--- ARQUIVO: {filename} ---\n{content}\n\n"
            except Exception as e:
                code_context += f"--- ARQUIVO: {filename} ---\n[ERRO DE SISTEMA] Não foi possível ler o arquivo '{filename}' do disco. Verifique os LOGS DE EXECUÇÃO abaixo para confirmar o conteúdo.\n\n"
    else:
        # Cenário B: Infraestrutura pura
        # Verifica se houve execução de comando bem-sucedida nos logs
        if logs and ("Success" in logs or "created" in logs or "exit_code 0" in logs.lower()):
             code_context = "ℹ️ NOTA DO SISTEMA: Esta tarefa foi identificada como puramente de infraestrutura/comandos. Nenhum arquivo de código foi modificado. Por favor, avalie o sucesso com base exclusivamente nos LOGS DE EXECUÇÃO abaixo."
        else:
             code_context = "⚠️ ALERTA: Nenhum arquivo foi modificado e não há evidência clara de comandos de sucesso. Verifique os logs com cautela."

    reviewer = CodeReviewAgent()
    verdict = reviewer.review_code(
        task_description=step.description,
        code_context=code_context,
        execution_logs=logs
    )
    
    return {"review_verdict": verdict}


def node_retry_handler(state: AgentState) -> dict:
    return {"retry_count": state["retry_count"] + 1}


def node_next_step_handler(state: AgentState) -> dict:
    """
    Apenas avança o índice do passo. A decisão de parar é do Router.
    """
    new_index = state["current_step_index"] + 1
    print(f"🔄 Avançando para o passo {new_index}...")
    return {
        "current_step_index": new_index,
        "retry_count": 0,
        "current_step": None,
        "review_verdict": None
    }


# --- EDGES (ROUTERS) ---

def check_review_outcome(state: AgentState) -> str:
    """Decide o destino após a revisão."""
    verdict = state.get("review_verdict")
    retry_count = state.get("retry_count", 0)
    
    if verdict and verdict.verdict == Verdict.PASS:
        return "success"
    
    # Permite até 3 tentativas de correção antes de abortar
    if retry_count < 3:
        return "retry"
    
    return "abort"


def plan_router(state: AgentState) -> str:
    """
    O 'Portão de Saída'. Verifica se ainda há passos no plano.
    Retorna: 'continue' (vai para executor) ou 'end' (encerra o grafo).
    """
    plan = state.get("plan")
    idx = state.get("current_step_index", 0)

    if not plan or not plan.steps:
        print("⚠️ Plano vazio ou inválido. Encerrando.")
        return "end"

    if idx < len(plan.steps):
        print(f"▶️ Executando passo {idx + 1} de {len(plan.steps)}...")
        return "continue"

    print("✅ Todos os passos concluídos com sucesso. Fim do workflow.")
    return "end"


# --- GRAPH CONSTRUCTION ---

def create_dev_graph(checkpointer=None, interrupt_before: list = None):
    workflow = StateGraph(AgentState)

    # 1. Adiciona Nós
    workflow.add_node("architect", node_architect)
    workflow.add_node("planner", node_planner)
    workflow.add_node("executor", node_executor)
    workflow.add_node("reviewer", node_reviewer)
    workflow.add_node("retry_handler", node_retry_handler)
    workflow.add_node("next_step_handler", node_next_step_handler)

    # 2. Define Fluxo Linear
    workflow.set_entry_point("architect")

    # Conecta Arquiteto ao Planejador
    workflow.add_edge("architect", "planner")

    # Ciclo de Retry
    workflow.add_edge("retry_handler", "executor")

    # Ciclo Principal
    workflow.add_edge("executor", "reviewer")

    # 3. Arestas Condicionais (Decisões)

    # Router Principal: Decide se executa ou para (pós-Planner)
    workflow.add_conditional_edges(
        "planner",
        plan_router,
        {"continue": "executor", "end": END}
    )

    # Router do Revisor
    workflow.add_conditional_edges(
        "reviewer",
        check_review_outcome,
        {
            "retry": "retry_handler",
            "abort": END,
            "success": "next_step_handler"
        }
    )

    # Router Principal: Decide se continua para o próximo passo ou encerra (pós-NextStep)
    workflow.add_conditional_edges(
        "next_step_handler",
        plan_router,
        {
            "continue": "executor",
            "end": END
        }
    )

    return workflow.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)
