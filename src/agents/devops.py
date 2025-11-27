from langchain_core.language_models.base import BaseLanguageModel

from src.core.agents.base import BaseAgent
from src.core.llm import LLM
from src.core.tools import SecureExecutorTool

class DevOpsAgent(BaseAgent):
    """
    Agent responsible for DevOps tasks, such as creating Dockerfiles, CI/CD pipelines, etc.
    """

    def __init__(self, llm: BaseLanguageModel = None, model_name: str = "smart"):
        super().__init__()
        self.llm = llm or LLM(model_name=model_name).get_llm()
        self.prompt_template = self._load_prompt_template("src/agents/devops_prompt.md")
        self.executor = SecureExecutorTool()

    def _create_prompt(self, task_description: str) -> str:
        """
        Creates a prompt for the agent to generate a Dockerfile.
        """
        return self.prompt_template.format(task_description=task_description)

    def execute(self, task_description: str) -> dict:
        """
        Generates a Dockerfile based on the project requirements.

        :param task_description: A description of the DevOps task.
        :return: A dictionary containing the generated file content and path.
        """
        prompt = self._create_prompt(task_description)
        response = self.llm.invoke(prompt)

        # Assuming the response is a markdown code block with the Dockerfile content
        file_content = self._parse_response(response.content)
        file_path = "Dockerfile"  # Or determine from task
        return {"file_path": file_path, "content": file_content}

    def _parse_response(self, response_content: str) -> str:
        """
        Parses the LLM response to extract the file content.
        """
        return response_content.strip().replace("```dockerfile", "").replace("```", "").strip()

    def create_environment(self, dockerfile_content: str, image_name: str = "dev-agent-env"):
        """
        Builds a Docker image from a Dockerfile.

        :param dockerfile_content: The content of the Dockerfile.
        :param image_name: The name for the Docker image.
        :return: The result of the docker build command.
        """
        with open("Dockerfile.tmp", "w") as f:
            f.write(dockerfile_content)

        build_command = f"docker build -t {image_name} -f Dockerfile.tmp ."
        result = self.executor.execute(build_command)
        return result
