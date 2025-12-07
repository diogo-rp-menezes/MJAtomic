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

        # Updated to use TECH_LEAD_MODEL (Google) instead of Orchestrator (Local)
        # We also remove base_url to ensure it uses the default provider (Google)
        # unless TECH_LEAD_BASE_URL is explicitly set.
        model_name = os.getenv("TECH_LEAD_MODEL", os.getenv("ORCHESTRATOR_MODEL", "gemini-2.5-pro"))
        # Force None for base_url to use Google provider logic in LLMProvider, unless strictly overridden
        # We ignore ORCHESTRATOR_BASE_URL here to ensure TechLead uses Google.
        self.llm = llm or LLM(model_name=model_name, base_url=None)

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

        try:
            # The LLMProvider now returns a valid Pydantic object (DevelopmentPlan) directly
            plan = self.llm.generate_response(prompt, schema=DevelopmentPlan)

            # Ensure it is the correct type (it should be, but good to be safe)
            if not isinstance(plan, DevelopmentPlan):
                raise TypeError(f"Expected DevelopmentPlan, got {type(plan)}")

            # Inject original_request if missing (recovery/consistency)
            if not plan.original_request:
                 plan.original_request = project_requirements

            return plan

        except Exception as e:
            self.logger.error(f"Failed to create development plan: {e}")
            raise

    def get_development_steps(self, plan: DevelopmentPlan) -> List[DevelopmentStep]:
        """
        Returns the list of development steps from the plan.
        """
        return plan.steps
