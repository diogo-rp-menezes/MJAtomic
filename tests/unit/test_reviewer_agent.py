import pytest
from unittest.mock import MagicMock, patch
from src.agents.reviewer.agent import CodeReviewAgent
from src.core.models import DevelopmentStep, TaskStatus, Verdict, CodeReviewVerdict

@pytest.fixture
def mock_reviewer_agent():
    with patch('src.agents.reviewer.agent.LLMProvider'), \
         patch('src.agents.reviewer.agent.CodeReviewAgent._load_prompt_template', return_value="Prompt: {task_description}"):

        agent = CodeReviewAgent()
        agent.llm = MagicMock()
        return agent

def test_review_code_pass_verdict(mock_reviewer_agent):
    """Test that a PASS verdict is returned correctly."""
    # Mock LLM to return valid JSON for CodeReviewVerdict
    mock_verdict = CodeReviewVerdict(verdict=Verdict.PASS, justification="Looks good")
    mock_reviewer_agent.llm.generate_response.return_value = mock_verdict.model_dump_json()

    verdict = mock_reviewer_agent.review_code(
        task_description="Implement feature",
        code_context="print('hello')",
        execution_logs="Success"
    )

    assert verdict.verdict == Verdict.PASS
    assert verdict.justification == "Looks good"

def test_review_code_fail_verdict(mock_reviewer_agent):
    """Test that a FAIL verdict is returned correctly."""
    mock_verdict = CodeReviewVerdict(verdict=Verdict.FAIL, justification="Syntax Error")
    mock_reviewer_agent.llm.generate_response.return_value = mock_verdict.model_dump_json()

    verdict = mock_reviewer_agent.review_code(
        task_description="Implement feature",
        code_context="print(",
        execution_logs="SyntaxError"
    )

    assert verdict.verdict == Verdict.FAIL
    assert verdict.justification == "Syntax Error"

def test_review_code_llm_crash(mock_reviewer_agent):
    """Test resilience against LLM failure (Fallback to FAIL)."""
    mock_reviewer_agent.llm.generate_response.side_effect = Exception("API Error")

    verdict = mock_reviewer_agent.review_code(
        task_description="Task",
        code_context="code",
        execution_logs="logs"
    )

    # Agent catches exception and returns FAIL verdict
    assert verdict.verdict == Verdict.FAIL
    assert "Falha crítica" in verdict.justification
