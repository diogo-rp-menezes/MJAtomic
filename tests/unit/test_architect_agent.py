import unittest
from unittest.mock import MagicMock, patch

from src.agents import ArchitectAgent


class TestArchitectAgent(unittest.TestCase):
    """
    Unit tests for the ArchitectAgent.
    """

    @patch("src.core.llm.LLM")
    def test_execute_success(self, mock_llm):
        # Mock the LLM's response
        mock_response = MagicMock()
        mock_response.content = "```\nsrc/main.py\ntests/test_main.py\n```"
        mock_llm.return_value.get_llm.return_value.invoke.return_value = mock_response

        agent = ArchitectAgent()
        result = agent.execute("A simple Python project")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertIn("src/main.py", result)

    def test_parse_response(self):
        agent = ArchitectAgent(llm=MagicMock())
        content = "```\nfile1.txt\nfolder/file2.py\n```"
        parsed = agent._parse_response(content)
        self.assertEqual(parsed, ["file1.txt", "folder/file2.py"])
