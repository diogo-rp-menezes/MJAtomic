from src.core.models import DevelopmentPlan, Step, AgentRole, TaskStatus
from src.core.llm.provider import LLMProvider
from src.tools.file_io import FileIOTool
from pydantic import BaseModel, Field
import uuid
import json
import re

class TechLeadAgent:
    def __init__(self, workspace_path: str = "./workspace"):
        self.llm_provider = LLMProvider(profile="smart")
        self.file_io = FileIOTool(root_path=workspace_path)

    def plan_task(self, user_request: str) -> DevelopmentPlan:
        return self.audit_and_plan(user_request)

    def audit_and_plan(self, user_request: str) -> DevelopmentPlan:
        project_context = self.file_io.get_project_structure()
        is_auto_audit = not user_request or len(user_request) < 5 or "audit" in user_request.lower()
        task_context = "AUTO-AUDIT & REPAIR" if is_auto_audit else user_request

        system_prompt = """
        Você é o DevAgent (inspirado no DevAgent). Você é um Engenheiro de Software Autônomo e Especialista.
        SUA FILOSOFIA:
        1. Entenda antes de agir.
        2. Segurança em primeiro lugar.
        3. TDD Estrito.
        4. Passos Atômicos.

        SUA MISSÃO AGORA:
        Analise o estado atual do projeto e o pedido do usuário: "{task_context}".
        Gere um plano de execução JSON claro:
        {{
            "steps": [
                {{"description": "[Setup] Inicializar Cargo.toml", "role": "FULLSTACK"}},
                {{"description": "[TDD-RED] Criar teste unitário", "role": "FULLSTACK"}}
            ]
        }}
        """

        user_msg = f"CONTEXTO DO PROJETO:\n{project_context}\n\nOBJETIVO: {task_context}"

        try:
            response_text = self.llm_provider.generate_response(user_msg, system_prompt)
            steps_data = self._parse_with_retry(response_text)
        except Exception as e:
            print(f"❌ [DevAgent] Erro de pensamento: {e}")
            steps_data = []

        if not steps_data:
            steps_data = [{"description": f"Diagnóstico falhou. Tentar abordagem direta: {task_context}", "role": "FULLSTACK"}]

        plan = DevelopmentPlan(original_request=task_context)
        valid_roles = [e.value for e in AgentRole]

        for s in steps_data:
            raw_role = s.get("role", "FULLSTACK").upper()
            final_role = AgentRole.FULLSTACK if raw_role not in valid_roles else AgentRole(raw_role)
            plan.steps.append(Step(id=str(uuid.uuid4()), description=s.get("description", "Tarefa"), role=final_role))
        return plan

    def _parse_with_retry(self, text: str) -> list:
        cleaned = re.sub(r'`json|`', '', text).strip()
        match_obj = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match_obj:
            try:
                data = json.loads(match_obj.group(0))
                if "steps" in data: return data["steps"]
            except: pass
        match_list = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if match_list:
            try: return json.loads(match_list.group(0))
            except: pass
        return []
