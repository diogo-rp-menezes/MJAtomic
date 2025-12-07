import logging
import os
from src.core.llm.provider import LLMProvider
from src.core.models import CodeReviewVerdict

class CodeReviewAgent:
    def __init__(self, llm_provider: LLMProvider = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        model_name = os.getenv("REVIEWER_MODEL", "gemini-2.5-flash")
        self.llm = llm_provider or LLMProvider(model_name=model_name)
        self.prompt_template = self._load_prompt_template("src/agents/reviewer/prompt.md")

    def _load_prompt_template(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Erro ao carregar o prompt {file_path}: {e}")
            raise

    def review_code(self, task_description: str, code_context: str, execution_logs: str) -> CodeReviewVerdict:
        """
        Analisa o código e retorna um veredito estruturado.
        """
        self.logger.info("🤖 [Reviewer] Analisando código...")

        prompt = self.prompt_template.format(
            task_description=task_description,
            code_context=code_context,
            execution_logs=execution_logs
        )

        try:
            # Usa o LLMProvider com o schema para garantir a saída estruturada (Pydantic object)
            verdict = self.llm.generate_response(prompt, schema=CodeReviewVerdict)

            if not isinstance(verdict, CodeReviewVerdict):
                 raise TypeError(f"Expected CodeReviewVerdict, got {type(verdict)}")

            self.logger.info(f"✅ [Reviewer] Veredito: {verdict.verdict}. Justificativa: {verdict.justification}")
            return verdict

        except Exception as e:
            self.logger.error(f"❌ [Reviewer] Falha crítica ao gerar ou validar o veredito: {e}")
            # Em caso de falha crítica, retorna um veredito de falha para segurança.
            return CodeReviewVerdict(
                verdict="FAIL",
                justification=f"Falha crítica no processo de revisão: {str(e)}"
            )
