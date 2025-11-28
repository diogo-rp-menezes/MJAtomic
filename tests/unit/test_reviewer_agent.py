import pytest
from unittest.mock import MagicMock, patch
from src.agents.reviewer.agent import CodeReviewAgent
from src.core.models import Step, TaskStatus

@pytest.fixture
def mock_reviewer_agent():
    with patch('src.agents.reviewer.agent.LLMProvider'), \
         patch('src.agents.reviewer.agent.FileIOTool'):
        agent = CodeReviewAgent(workspace_path="/tmp/test_workspace")
        agent.llm = MagicMock()
        agent.file_io = MagicMock()
        return agent

def test_review_step_pass_verdict(mock_reviewer_agent):
    """Test that a PASS verdict keeps the step status."""
    step = Step(id="1", description="Implement feature", role="FULLSTACK", status="COMPLETED")
    step.logs = "Arquivos gerados: ['main.py']"

    mock_reviewer_agent.file_io.read_file.return_value = "print('hello')"
    mock_reviewer_agent.llm.generate_response.return_value = "VERDICT: PASS\nGood job."

    reviewed_step = mock_reviewer_agent.review_step(step)

    assert "VERDICT: PASS" in reviewed_step.logs
    assert reviewed_step.status == TaskStatus.COMPLETED
