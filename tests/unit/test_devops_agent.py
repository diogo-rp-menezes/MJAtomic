import unittest
from unittest.mock import MagicMock, patch

from src.agents import DevOpsAgent


class TestDevOpsAgent(unittest.TestCase):
    """
    Unit tests for the DevOpsAgent.
    """

    @patch("src.core.llm.LLM")
    def test_execute_generates_dockerfile(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "```dockerfile\nFROM python:3.11\n```"
        mock_llm.return_value.get_llm.return_value.invoke.return_value = mock_response

        agent = DevOpsAgent()
        result = agent.execute("Create a Dockerfile for a Python app")

        self.assertIn("file_path", result)
        self.assertIn("content", result)
        self.assertEqual(result["file_path"], "Dockerfile")
        self.assertIn("FROM python:3.11", result["content"])

    @patch("src.core.tools.SecureExecutorTool")
    def test_create_environment(self, mock_executor):
        agent = DevOpsAgent(llm=MagicMock())
        dockerfile_content = "FROM python:3.11"
        
        agent.create_environment(dockerfile_content)

        mock_executor.return_value.execute.assert_called_once()
        # More specific assertions can be added here
