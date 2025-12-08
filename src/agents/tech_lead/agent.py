import logging
import os
from typing import List

from src.core.agents.base import BaseAgent
from src.core.interfaces import ILLMProvider
from src.core.models import DevelopmentPlan, DevelopmentStep


class TechLeadAgent(BaseAgent):
    """
    Agent responsible for creating a development plan from project requirements.
    """

    def __init__(
        self,
        llm: ILLMProvider,
        workspace_path: str = "./workspace"
    ):
        super().__init__()
        self.workspace_path = workspace_path
        self.logger = logging.getLogger(self.__class__.__name__)
        self.llm = llm

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
