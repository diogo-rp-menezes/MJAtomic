import logging
import os
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
        self, llm: Optional[BaseLanguageModel] = None, workspace_path: str = "./workspace"
    ):
        super().__init__()
        self.workspace_path = workspace_path
        self.logger = logging.getLogger(self.__class__.__name__)

        model_name = os.getenv("ORCHESTRATOR_MODEL", "llama3.2")
        base_url = os.getenv("ORCHESTRATOR_BASE_URL")
        self.llm = llm or LLM(model_name=model_name, base_url=base_url)

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

        # A resposta já é um JSON garantido pelo schema, basta validar.
        try:
            return DevelopmentPlan.model_validate_json(response_json)
        except Exception as e:
            self.logger.warning(f"Initial validation failed: {e}. Attempting recovery by injecting metadata.")
            try:
                data = json.loads(response_json)
                if isinstance(data, dict):
                    # Injeta original_request se estiver faltando
                    if "original_request" not in data or not data["original_request"]:
                        data["original_request"] = project_requirements

                    # Validate again with injected data
                    return DevelopmentPlan.model_validate(data)
                else:
                    raise ValueError("Parsed JSON is not a dictionary.")
            except Exception as retry_e:
                self.logger.error(f"Failed to validate development plan after recovery attempt: {retry_e}")
                self.logger.error(f"Received JSON: {response_json}")
                raise ValueError("Could not validate the development plan JSON.") from retry_e

    def get_development_steps(self, plan: DevelopmentPlan) -> List[DevelopmentStep]:
        """
        Returns the list of development steps from the plan.
        """
        return plan.steps
