import unittest
from unittest.mock import MagicMock, patch

from src.agents import TechLeadAgent
from src.core.models import DevelopmentPlan


class TestTechLeadAgent(unittest.TestCase):
    """
    Unit tests for the TechLeadAgent.
    """

    @patch("src.core.llm.LLM")
    def test_create_development_plan_success(self, mock_llm):
        # Arrange
        mock_response_content = """
        ```json
        {
          "project_name": "Test API",
          "tasks": ["Implement endpoint"],
          "steps": [
            {
              "step": "Write test for endpoint",
              "task": "Implement endpoint",
              "language": "python",
              "test_command": "pytest"
            }
          ]
        }
        ```
        """
        mock_response = MagicMock(content=mock_response_content)
        mock_llm.return_value.get_llm.return_value.invoke.return_value = mock_response

        agent = TechLeadAgent()

        # Act
        plan = agent.create_development_plan("A test project", "python")

        # Assert
        self.assertIsInstance(plan, DevelopmentPlan)
        self.assertEqual(plan.project_name, "Test API")
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].step, "Write test for endpoint")

    @patch("src.core.llm.LLM")
    def test_create_development_plan_failure(self, mock_llm):
        # Arrange
        mock_response = MagicMock(content="Invalid JSON")
        mock_llm.return_value.get_llm.return_value.invoke.return_value = mock_response

        agent = TechLeadAgent()

        # Act & Assert
        with self.assertRaises(ValueError):
            agent.create_development_plan("A test project", "python")

    def test_parse_response_with_malformed_json(self):
        agent = TechLeadAgent(llm=MagicMock())
        content = "```json\n{'project_name': 'Test'}\n```" # Using single quotes is invalid JSON
        result = agent._parse_response(content)
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
