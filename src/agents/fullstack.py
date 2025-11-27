import json
import logging
import re
from typing import Optional

from langchain_core.language_models.base import BaseLanguageModel

from src.core.agents.base import BaseAgent
from src.core.llm import LLM
from src.core.memory import VectorMemory
from src.core.models import (CodeExecution, CodeExecutionResult,
                             DevelopmentStep, TestExecutionResult)
from src.core.tools import CodeIndexerTool, SecureExecutorTool


class FullstackAgent(BaseAgent):
    """
    Agent responsible for writing and fixing code, including tests, based on a development plan.
    It follows a TDD (Test-Driven Development) approach.
    """

    def __init__(
        self,
        llm: Optional[BaseLanguageModel] = None,
        model_name: str = "smart",
        memory: Optional[VectorMemory] = None,
        indexer: Optional[CodeIndexerTool] = None,
    ):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.llm = llm or LLM(model_name=model_name).get_llm()
        self.prompt_template = self._load_prompt_template("src/agents/fullstack_prompt.md")
        self.executor = SecureExecutorTool()
        self.memory = memory or self._initialize_memory()
        self.indexer = indexer or CodeIndexerTool(self.memory.vector_store)

        if not self.memory.is_initialized():
            self.logger.warning("Memory not initialized. Indexing workspace.")
            self.indexer.index_workspace()

    def _initialize_memory(self) -> VectorMemory:
        try:
            return VectorMemory()
        except Exception as e:
            self.logger.error(f"Failed to initialize VectorMemory: {e}")
            # Degraded mode: operate without RAG capabilities
            return VectorMemory(initialized=False)

    def _get_context(self, prompt: str) -> str:
        """Retrieves relevant context from the vector memory."""
        if not self.memory.is_initialized():
            return "No context available due to memory initialization failure."

        try:
            return self.memory.retrieve_context(prompt)
        except Exception as e:
            self.logger.error(f"Error retrieving context from memory: {e}")
            return "Failed to retrieve context."

    def execute_task(self, step: DevelopmentStep) -> CodeExecution:
        """
        Executes a single development step, which can be writing a test or implementing code.
        """
        self.logger.info(f"Executing step: {step.step}")
        self.logger.info(f"Task: {step.task}")

        prompt = self._create_prompt(step)
        response = self.llm.invoke(prompt)
        parsed_response = self._parse_response(response.content)

        file_path = parsed_response.get("file_path")
        code = parsed_response.get("code")

        if not file_path or not code:
            self.logger.error("Failed to parse file_path or code from LLM response.")
            raise ValueError("Invalid response from LLM, missing file_path or code.")

        self.write_code(file_path, code)

        return CodeExecution(file_path=file_path, code=code)

    def run_tests(self, test_command: str) -> TestExecutionResult:
        """
        Runs the specified test command in the secure execution environment.
        """
        self.logger.info(f"Running tests with command: {test_command}")
        result = self.executor.execute(test_command)
        return TestExecutionResult(
            command=test_command,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def fix_code(
        self,
        step: DevelopmentStep,
        code_execution: CodeExecution,
        test_result: TestExecutionResult,
        max_retries: int = 3,
    ) -> CodeExecutionResult:
        """
        Attempts to fix the code based on test failures. This is the "self-healing" mechanism.
        """
        self.logger.info("Attempting to fix code based on test results.")
        retries = 0
        current_code = code_execution.code

        while retries < max_retries:
            self.logger.info(f"Fix attempt {retries + 1}/{max_retries}")

            prompt = self._create_fix_prompt(step, current_code, test_result)
            response = self.llm.invoke(prompt)
            parsed_response = self._parse_response(response.content)

            new_code = parsed_response.get("code")
            file_path = parsed_response.get("file_path", code_execution.file_path)

            if not new_code:
                self.logger.error("LLM failed to provide new code for the fix.")
                retries += 1
                continue

            self.write_code(file_path, new_code)
            current_code = new_code

            # Re-run tests to see if the fix was successful
            test_result = self.run_tests(step.test_command)
            if test_result.exit_code == 0:
                self.logger.info("Code fixed successfully!")
                return CodeExecutionResult(
                    code_execution=CodeExecution(file_path=file_path, code=current_code),
                    test_result=test_result,
                    status="FIXED",
                )

            self.logger.warning("Fix did not resolve the issue. Retrying.")
            retries += 1

        self.logger.error("Failed to fix code after multiple attempts.")
        return CodeExecutionResult(
            code_execution=CodeExecution(file_path=file_path, code=current_code),
            test_result=test_result,
            status="FAILED_TO_FIX",
        )

    def write_code(self, file_path: str, code: str):
        """
        Writes the given code to the specified file.
        """
        self.logger.info(f"Writing code to {file_path}")
        # This command creates the directory if it doesn't exist
        self.executor.execute(f"mkdir -p $(dirname {file_path})")
        # Now, write the file
        self.executor.write_file(file_path, code)

    def _create_prompt(self, step: DevelopmentStep) -> str:
        """
        Creates the prompt for the LLM to either write a test or implement code.
        """
        context = self._get_context(step.task)
        return self.prompt_template.format(
            task=step.task,
            step=step.step,
            code_language=step.language,
            context=context,
            instruction_type="implement the code",
        )

    def _create_fix_prompt(
        self, step: DevelopmentStep, code: str, test_result: TestExecutionResult
    ) -> str:
        """
        Creates the prompt for the LLM to fix the code based on test results.
        """
        context = self._get_context(step.task)
        error_log = f"STDOUT:\n{test_result.stdout}\n\nSTDERR:\n{test_result.stderr}"

        return self.prompt_template.format(
            task=step.task,
            step=step.step,
            code_language=step.language,
            context=context,
            instruction_type=f"fix the following code:\n\n```python\n{code}\n```\n\nBased on the following test results:\n\n{error_log}",
        )

    def _parse_response(self, response_content: str) -> dict:
        """
        Parses the LLM's response to extract the file path and code.
        The response is expected to be a JSON object within a markdown block.
        """
        try:
            # Use regex to find the JSON block
            json_match = re.search(r"```json\n({.*?})\n```", response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                self.logger.warning("No JSON block found in the response. Trying to parse the whole content.")
                # Fallback for cases where the LLM doesn't follow the format perfectly
                return json.loads(response_content)
        except (json.JSONDecodeError, AttributeError) as e:
            self.logger.error(f"Error parsing LLM response: {e}\nResponse content: {response_content}")
            return {}

