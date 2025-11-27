from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate

from src.core.agents.base import BaseAgent
from src.core.llm import LLM

class ArchitectAgent(BaseAgent):
    """
    Agent responsible for designing the software architecture and project structure.
    """

    def __init__(self, llm: BaseLanguageModel = None, model_name: str = "smart"):
        super().__init__()
        self.llm = llm or LLM(model_name=model_name).get_llm()
        self.prompt_template = self._load_prompt_template("src/agents/architect_prompt.md")

    def _create_prompt(self, project_requirements: str) -> ChatPromptTemplate:
        """
        Creates a prompt for the agent to design the project structure.
        """
        return self.prompt_template.format(project_requirements=project_requirements)

    def execute(self, project_requirements: str) -> list[str]:
        """
        Designs the project structure based on the project requirements.

        :param project_requirements: The requirements for the project.
        :return: A list of file paths representing the project structure.
        """
        prompt = self._create_prompt(project_requirements)
        response = self.llm.invoke(prompt)

        # Assuming the response is a markdown code block with the file structure
        file_paths = self._parse_response(response.content)
        return file_paths

    def _parse_response(self, response_content: str) -> list[str]:
        """
        Parses the LLM response to extract the file paths.
        """
        # A simple parser for a list of files in a markdown block
        lines = response_content.strip().split('\n')
        file_paths = [
            line.strip() for line in lines
            if line.strip() and not line.startswith("```")
        ]
        return file_paths
