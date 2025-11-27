import unittest
from unittest.mock import MagicMock, patch

from src.agents import ReviewerAgent
from src.core.models import CodeReview, DevelopmentStep


class TestReviewerAgent(unittest.TestCase):
    """
    Unit tests for the ReviewerAgent.
    """

    @patch("src.core.llm.LLM")
    def test_review_code_approved(self, mock_llm):
        # Arrange
        mock_response = MagicMock(content="{'approved': True, 'comments': 'LGTM!'}")
        mock_llm.return_value.get_llm.return_value.invoke.return_value = mock_response
        
        agent = ReviewerAgent()
        step = DevelopmentStep(
            step="Implement login", task="Auth", language="python", test_command="pytest"
        )
        code = "def login(): return True"

        # Act
        review = agent.review_code(step, code)

        # Assert
        self.assertIsInstance(review, CodeReview)
        self.assertTrue(review.approved)
        self.assertEqual(review.comments, "LGTM!")

    @patch("src.core.llm.LLM")
    def test_review_code_rejected(self, mock_llm):
        # Arrange
        mock_response = MagicMock(content="{'approved': False, 'comments': 'Needs improvement.'}")
        mock_llm.return_value.get_llm.return_value.invoke.return_value = mock_response

        agent = ReviewerAgent()
        step = DevelopmentStep(
            step="Implement login", task="Auth", language="python", test_command="pytest"
        )
        code = "def login(): return"

        # Act
        review = agent.review_code(step, code)

        # Assert
        self.assertFalse(review.approved)
        self.assertEqual(review.comments, "Needs improvement.")

    def test_parse_response_failure(self):
        agent = ReviewerAgent(llm=MagicMock())
        invalid_content = "This is not a dict"
        result = agent._parse_response(invalid_content)
        self.assertFalse(result["approved"])
        self.assertEqual(result["comments"], "Failed to parse review.")

if __name__ == "__main__":
    unittest.main()
