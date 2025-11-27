from langchain_core.language_models.base import BaseLanguageModel

from src.core.agents.base import BaseAgent
from src.core.llm import LLM
from src.core.models import CodeReview, DevelopmentStep


class ReviewerAgent(BaseAgent):
    """
    Agent responsible for reviewing code for quality, correctness, and adherence to standards.
    """

    def __init__(self, llm: BaseLanguageModel = None, model_name: str = "smart"):
        super().__init__()
        self.llm = llm or LLM(model_name=model_name).get_llm()
        self.prompt_template = self._load_prompt_template("src/agents/reviewer_prompt.md")

    def _create_prompt(self, step: DevelopmentStep, code: str) -> str:
        """
        Creates a prompt for the agent to review the code.
        """
        return self.prompt_template.format(
            task=step.task,
            step=step.step,
            code_language=step.language,
            code=code,
        )

    def review_code(self, step: DevelopmentStep, code: str) -> CodeReview:
        """
        Reviews the provided code based on the development step.

        :param step: The development step that the code is supposed to implement.
        :param code: The code to be reviewed.
        :return: A CodeReview object with the review results.
        """
        prompt = self._create_prompt(step, code)
        response = self.llm.invoke(prompt)

        # Assuming the response is a structured format (e.g., JSON)
        review_results = self._parse_response(response.content)

        return CodeReview(
            approved=review_results.get("approved", False),
            comments=review_results.get("comments", "No comments provided."),
        )

    def _parse_response(self, response_content: str) -> dict:
        """
        Parses the LLM response to extract the review results.
        Expected format is a JSON object with 'approved' (bool) and 'comments' (str).
        """
        try:
            # A simple parser for a JSON response
            return eval(response_content)
        except Exception as e:
            print(f"Error parsing review response: {e}")
            return {"approved": False, "comments": "Failed to parse review."}
