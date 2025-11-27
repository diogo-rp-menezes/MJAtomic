import unittest
from unittest.mock import MagicMock, patch

from src.agents import (ArchitectAgent, DevOpsAgent, FullstackAgent,
                         ReviewerAgent, TechLeadAgent)
from src.core.models import CodeReview, DevelopmentPlan


class TestFullAgentChain(unittest.TestCase):
    """
    Integration tests for the full chain of agents, using mocks for external dependencies.
    """

    @patch("src.core.llm.LLM")
    def test_planning_phase(self, mock_llm):
        # Mocking the LLM responses
        mock_llm.return_value.get_llm.return_value.invoke.side_effect = [
            MagicMock(
                content='```json\n{"project_name": "Test", "tasks": [], "steps": []}\n```'
            ),  # TechLead
            MagicMock(content="```\nsrc/main.py\ntests/test_main.py\n```"),  # Architect
        ]

        tech_lead = TechLeadAgent()
        architect = ArchitectAgent()

        plan = tech_lead.create_development_plan("Test Project", "python")
        structure = architect.execute("Test Project")

        self.assertIsInstance(plan, DevelopmentPlan)
        self.assertEqual(plan.project_name, "Test")
        self.assertIsInstance(structure, list)
        self.assertIn("src/main.py", structure)

    @patch("src.agents.FullstackAgent")
    @patch("src.agents.ReviewerAgent")
    def test_execution_and_review_phase(self, mock_reviewer_agent, mock_fullstack_agent):
        # Mocking the agents' behavior
        mock_fullstack_agent.return_value.execute_task.return_value = MagicMock(
            file_path="src/main.py", code="print('hello')"
        )
        mock_reviewer_agent.return_value.review_code.return_value = CodeReview(
            approved=True, comments="Looks good."
        )

        fullstack = mock_fullstack_agent()
        reviewer = mock_reviewer_agent()

        step = MagicMock()
        code_execution = fullstack.execute_task(step)
        review = reviewer.review_code(step, code_execution.code)

        self.assertEqual(code_execution.file_path, "src/main.py")
        self.assertTrue(review.approved)
