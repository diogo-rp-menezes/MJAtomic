import unittest
from unittest.mock import MagicMock, patch

from src.agents.fullstack import FullstackAgent
from src.core.models import (CodeExecution, DevelopmentStep,
                             TestExecutionResult)


class TestFullstackAgent(unittest.TestCase):
    """
    Unit tests for the FullstackAgent.
    """

    def setUp(self):
        # Create a mock for the LLM
        self.mock_llm = MagicMock()

        # Create a mock for the executor
        self.mock_executor = MagicMock()

        # Create a mock for memory and indexer
        self.mock_memory = MagicMock()
        self.mock_memory.is_initialized.return_value = True
        self.mock_memory.retrieve_context.return_value = "Some relevant context."
        self.mock_indexer = MagicMock()

        # Initialize the agent with mocks
        self.agent = FullstackAgent(
            llm=self.mock_llm,
            memory=self.mock_memory,
            indexer=self.mock_indexer
        )
        self.agent.executor = self.mock_executor

    def test_execute_task_writes_code(self):
        # Arrange
        step = DevelopmentStep(
            step="Implement the login function",
            task="User Authentication",
            language="python",
            test_command="pytest tests/test_auth.py",
        )
        llm_response = MagicMock(
            content='```json\n{"file_path": "src/auth.py", "code": "def login(): pass"}\n```'
        )
        self.mock_llm.invoke.return_value = llm_response

        # Act
        result = self.agent.execute_task(step)

        # Assert
        self.mock_llm.invoke.assert_called_once()
        self.mock_executor.write_file.assert_called_with("src/auth.py", "def login(): pass")
        self.assertEqual(result.file_path, "src/auth.py")

    def test_run_tests_executes_command(self):
        # Arrange
        test_command = "pytest"
        self.mock_executor.execute.return_value = MagicMock(exit_code=0, stdout=".", stderr="")

        # Act
        result = self.agent.run_tests(test_command)

        # Assert
        self.mock_executor.execute.assert_called_with(test_command)
        self.assertEqual(result.exit_code, 0)

    def test_fix_code_successful(self):
        # Arrange
        step = DevelopmentStep(
            step="Fix login function",
            task="User Authentication",
            language="python",
            test_command="pytest",
        )
        code_execution = CodeExecution(file_path="src/auth.py", code="def login(): return False")
        test_result = TestExecutionResult(command="pytest", exit_code=1, stdout="F", stderr="AssertionError")

        # Mock LLM to provide a fix
        llm_fix_response = MagicMock(
            content='```json\n{"file_path": "src/auth.py", "code": "def login(): return True"}\n```'
        )
        self.mock_llm.invoke.return_value = llm_fix_response
        
        # Mock executor to return success after the fix
        self.mock_executor.execute.return_value = MagicMock(exit_code=0, stdout=".", stderr="")

        # Act
        result = self.agent.fix_code(step, code_execution, test_result)

        # Assert
        self.assertEqual(result.status, "FIXED")
        self.assertEqual(result.code_execution.code, "def login(): return True")

    def test_parse_response_failure(self):
        # Arrange
        invalid_response = "This is not a JSON"

        # Act
        result = self.agent._parse_response(invalid_response)

        # Assert
        self.assertEqual(result, {})

if __name__ == "__main__":
    unittest.main()
