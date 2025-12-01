import logging
import json
from typing import List, Optional

from langchain_core.language_models.base import BaseLanguageModel

from src.core.agents.base import BaseAgent
from src.core.llm.provider import LLMProvider as LLM
from src.core.models import DevelopmentPlan, DevelopmentStep


class TechLeadAgent(BaseAgent):
    """
    Agent responsible for creating a development plan from project requirements.
    """

    def __init__(
        self, llm: Optional[BaseLanguageModel] = None, model_name: str = "smart", workspace_path: str = "./workspace"
    ):
        super().__init__()
        self.workspace_path = workspace_path
        self.logger = logging.getLogger(self.__class__.__name__)
        self.llm = llm or LLM(profile=model_name)
        self.prompt_template = self._load_prompt_template(
            "src/agents/tech_lead_prompt.md"
        )

    def create_development_plan(
        self, project_requirements: str, code_language: str
    ) -> DevelopmentPlan:
        """
        Creates a development plan based on the project requirements using structured output.
        """
        prompt = self.prompt_template.format(
            project_requirements=project_requirements, code_language=code_language
        )

        # A chamada agora delega a complexidade para o LLMProvider e espera um JSON.
        response_json = self.llm.generate_response(prompt, schema=DevelopmentPlan)

        if not response_json or response_json.strip() == "{}":
            self.logger.error("LLM returned an empty response.")
            raise ValueError("LLM returned an empty response, cannot create a development plan.")

        # A resposta já é um JSON garantido pelo schema, basta validar.
        try:
            data = json.loads(response_json)
            data['original_request'] = project_requirements
            return DevelopmentPlan(**data)
        except Exception as e:
            self.logger.error(f"Failed to validate development plan from LLM response: {e}")
            self.logger.error(f"Received JSON: {response_json}")
            # Retorna um plano vazio ou lança uma exceção para indicar falha crítica
            raise ValueError("Could not validate the development plan JSON.") from e

    def get_development_steps(self, plan: DevelopmentPlan) -> List[DevelopmentStep]:
        """
        Returns the list of development steps from the plan.
        """
        return plan.steps
