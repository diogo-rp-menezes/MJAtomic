import pytest
from unittest.mock import MagicMock, patch
from src.agents.reviewer.agent import CodeReviewAgent
from src.core.models import DevelopmentStep, TaskStatus

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
    step = DevelopmentStep(id="1", description="Implement feature", role="FULLSTACK", status="COMPLETED")
    step.logs = "Arquivos gerados: ['main.py']"

    mock_reviewer_agent.file_io.read_file.return_value = "print('hello')"
    mock_reviewer_agent.llm.generate_response.return_value = "VERDICT: PASS\nGood job."

    reviewed_step = mock_reviewer_agent.review_step(step)

    assert "VERDICT: PASS" in reviewed_step.logs
    assert reviewed_step.status == TaskStatus.COMPLETED

def test_review_step_fail_verdict(mock_reviewer_agent):
    """Test that a FAIL verdict is logged (status change is optional in current logic)."""
    step = DevelopmentStep(id="1", description="Implement feature", role="FULLSTACK", status="COMPLETED")
    step.logs = "Arquivos gerados: ['main.py']"

    mock_reviewer_agent.file_io.read_file.return_value = "syntax error"
    mock_reviewer_agent.llm.generate_response.return_value = "VERDICT: FAIL\nSyntax error."

    reviewed_step = mock_reviewer_agent.review_step(step)

    assert "VERDICT: FAIL" in reviewed_step.logs
    # In the current implementation, it returns the step without changing status to FAILED automatically
    # unless implemented. This test confirms the current behavior.
    assert reviewed_step.status == TaskStatus.COMPLETED

def test_review_step_no_files_found(mock_reviewer_agent):
    """Test fallback when no files are in logs."""
    step = DevelopmentStep(id="1", description="Task", role="FULLSTACK")
    step.logs = "No files listed"

    # Mock os.walk to return nothing
    with patch("os.walk", return_value=[]):
        reviewed_step = mock_reviewer_agent.review_step(step)

    assert "Nada para revisar" in reviewed_step.logs
    assert "VERDICT: PASS" in reviewed_step.logs

def test_review_step_llm_crash(mock_reviewer_agent):
    """Test resilience against LLM failure (Soft Fail)."""
    step = DevelopmentStep(id="1", description="Task", role="FULLSTACK")
    step.logs = "Arquivos gerados: ['main.py']"

    mock_reviewer_agent.file_io.read_file.return_value = "code"
    mock_reviewer_agent.llm.generate_response.side_effect = Exception("API Error")

    reviewed_step = mock_reviewer_agent.review_step(step)

    assert "Falha na IA" in reviewed_step.logs
    assert "VERDICT: PASS (Soft Fail)" in reviewed_step.logs
