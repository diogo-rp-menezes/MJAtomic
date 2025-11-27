import json
import logging
import re
from typing import List, Optional

from langchain_core.language_models.base import BaseLanguageModel

from src.core.agents.base import BaseAgent
from src.core.llm import LLM
from src.core.models import DevelopmentPlan, DevelopmentStep


class TechLeadAgent(BaseAgent):
    """
    Agent responsible for creating a development plan from project requirements.
    """

    def __init__(
        self, llm: Optional[BaseLanguageModel] = None, model_name: str = "smart"
    ):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.llm = llm or LLM(model_name=model_name).get_llm()
        self.prompt_template = self._load_prompt_template(
            "src/agents/tech_lead_prompt.md"
        )

    def create_development_plan(
        self, project_requirements: str, code_language: str
    ) -> DevelopmentPlan:
        """
        Creates a development plan based on the project requirements.

        :param project_requirements: The high-level requirements for the project.
        :param code_language: The primary programming language for the project.
        :return: A DevelopmentPlan object.
        """
        prompt = self.prompt_template.format(
            project_requirements=project_requirements, code_language=code_language
        )
        response = self.llm.invoke(prompt)
        parsed_plan = self._parse_response(response.content)

        if not parsed_plan:
            self.logger.error("Failed to parse development plan from LLM response.")
            raise ValueError("Could not parse the development plan.")

        steps = [DevelopmentStep(**step) for step in parsed_plan.get("steps", [])]
        return DevelopmentPlan(
            project_name=parsed_plan.get("project_name", "Unnamed Project"),
            tasks=parsed_plan.get("tasks", []),
            steps=steps,
        )

    def _parse_response(self, response_content: str) -> Optional[dict]:
        """
        Parses the LLM's response to extract the development plan.
        The response is expected to be a JSON object within a markdown block.
        """
        try:
            # Enhanced regex to find JSON object or list
            json_match = re.search(
                r"```json\s*([\s\S]*?)\s*```", response_content, re.DOTALL
            )
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                self.logger.warning(
                    "No JSON block found in the response. Trying to parse the whole content."
                )
                # Fallback for cases where the LLM doesn't follow the format perfectly
                return json.loads(response_content)
        except (json.JSONDecodeError, AttributeError) as e:
            self.logger.error(
                f"Error parsing LLM response: {e}\nResponse content: {response_content}"
            )
            return None

    def get_development_steps(self, plan: DevelopmentPlan) -> List[DevelopmentStep]:
        """
        Returns the list of development steps from the plan.
        """
        return plan.steps
