from abc import ABC, abstractmethod

from langchain_core.prompts import PromptTemplate


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    """



    def __init__(self):
        self.prompt_template = None

    def _load_prompt_template(self, file_path: str) -> PromptTemplate:
        """

        Loads a prompt template from a file.
        """
        with open(file_path, "r") as f:
            template_str = f.read()
        return PromptTemplate.from_template(template_str)

    @abstractmethod
    def execute(self, *args, **kwargs):
        """
        The main method to execute the agent's task.
        """
        pass
