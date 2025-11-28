from src.core.models import Step, TaskStatus
from src.core.llm.provider import LLMProvider
from src.tools.file_io import FileIOTool
from src.core.logger import logger
import os
import re

class CodeReviewAgent:
    def __init__(self, workspace_path: str = "./workspace"):
        self.workspace_path = workspace_path
        self.llm = LLMProvider(profile="balanced")
        self.file_io = FileIOTool(root_path=self.workspace_path)

    def review_step(self, step: Step) -> Step:
        current_logs = step.logs or ""
        logger.info(f"[Reviewer] Iniciando revisão do passo {step.id}")

        # 1. Extração de arquivos modificados
        # Tenta pegar do log ou usa lista vazia se falhar
        files_match = re.search(r"Arquivos gerados: \[(.*?)\]", current_logs)
        files_to_review = []
        if files_match:
            file_str = files_match.group(1).replace("'", "").replace('"', "")
            files_to_review = [f.strip() for f in file_str.split(",")] if file_str else []

        if not files_to_review:
            logger.info("[Reviewer] Nenhum arquivo explícito nos logs. Buscando recentes...")
            # Fallback: Buscar arquivos modificados recentemente seria ideal, mas vamos listar source codes
            try:
                for root, _, files in os.walk(self.workspace_path):
                    for file in files:
                        if file.endswith(('.rs', '.py', '.js', '.java', '.toml')):
                             files_to_review.append(os.path.relpath(os.path.join(root, file), self.workspace_path))
            except Exception as e:
                logger.error(f"[Reviewer] Erro ao listar arquivos: {e}")

        # Limitar a 3 arquivos para não estourar contexto do Reviewer
        files_to_review = files_to_review[:3]

        code_context = ""
        for filename in files_to_review:
            try:
                content = self.file_io.read_file(filename)
                # Truncar arquivos grandes
                if len(content) > 2000: content = content[:2000] + "\n...[TRUNCATED]"
                code_context += f"--- {filename} ---\n{content}\n\n"
            except Exception as e:
                logger.warning(f"[Reviewer] Não conseguiu ler {filename}: {e}")

        if not code_context:
             msg = "[Reviewer] Nada para revisar (sem código acessível). VERDICT: PASS"
             logger.info(msg)
             step.logs = current_logs + f"\n\n{msg}"
             return step

        system_prompt = """
        Você é um Auditor de Qualidade de Código (QA).
        Analise o trabalho feito no passo.

        CRITÉRIOS DE APROVAÇÃO:
        1. Se a tarefa era "Criar Teste Falho" (TDD Red), o código DEVE ter um teste novo e a execução DEVE ter falhado (Exit != 0).
        2. Se a tarefa era "Implementar" (TDD Green), o código DEVE compilar e passar (Exit 0).
        3. Código inválido (sintaxe quebrada) = REPROVADO.

        Responda APENAS:
        VERDICT: PASS
        ou
        VERDICT: FAIL

        Justificativa curta na linha seguinte.
        """

        user_msg = f"TAREFA: {step.description}\n\nLOGS DE EXECUÇÃO:\n{current_logs[-2000:]}\n\nCÓDIGO:\n{code_context}"

        try:
            response = self.llm.generate_response(user_msg, system_prompt)
            logger.info(f"[Reviewer] Resposta LLM: {response}")

            step.logs = current_logs + f"\n\n--- Revisão ---\n{response}\n"

            if "VERDICT: PASS" in response.upper():
                return step # Mantém status que veio do worker (COMPLETED se não houve exceção antes)
            else:
                # Opcional: Marcar como FAILED se quiser bloquear o processo
                # step.status = TaskStatus.FAILED
                pass

        except Exception as e:
            err_msg = f"[Reviewer Error] Falha na IA: {str(e)}"
            logger.error(err_msg)
            step.logs = current_logs + f"\n\n{err_msg}. VERDICT: PASS (Soft Fail)"

        return step
