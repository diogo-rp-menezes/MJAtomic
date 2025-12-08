import pytest
from unittest.mock import MagicMock
import json
from src.agents.fullstack.agent import FullstackAgent
from src.core.models import DevelopmentStep, TaskStatus

@pytest.fixture
def mock_fullstack_agent():
    llm = MagicMock()
    prompt_builder = MagicMock()
    response_handler = MagicMock()

    # Configure PromptBuilder defaults
    prompt_builder.build_system_prompt.return_value = "System Prompt"
    prompt_builder.build_context.return_value = "Context"

    agent = FullstackAgent(
        llm=llm,
        prompt_builder=prompt_builder,
        response_handler=response_handler,
        workspace_path="/tmp/test_workspace"
    )
    return agent

def test_execute_step_success(mock_fullstack_agent):
    """Test execute_step successful run delegating to components."""
    step = DevelopmentStep(id="1", description="Implement feature", role="FULLSTACK")

    # Mock LLM
    mock_fullstack_agent.llm.generate_response.return_value = '{"command": "foo"}'

    # Mock ResponseHandler: (output_log, created_files, success)
    mock_fullstack_agent.response_handler.handle.return_value = ("Success output", ["file.py"], True)

    result_step, files = mock_fullstack_agent.execute_step(step)

    assert result_step.status == TaskStatus.COMPLETED
    assert "Success output" in result_step.logs
    assert files == ["file.py"]

    # Verify delegation
    mock_fullstack_agent.prompt_builder.build_context.assert_called()
    mock_fullstack_agent.llm.generate_response.assert_called()
    mock_fullstack_agent.response_handler.handle.assert_called_once()

def test_execute_step_retry_logic(mock_fullstack_agent):
    """Test self-healing retry logic."""
    step = DevelopmentStep(id="1", description="Implement feature", role="FULLSTACK")

    # Always return valid JSON structure for this test
    mock_fullstack_agent.llm.generate_response.return_value = '{"command": "cmd"}'

    # Attempt 1: Fail, Attempt 2: Success
    mock_fullstack_agent.response_handler.handle.side_effect = [
        ("Error output", [], False),
        ("Passed output", ["fixed.py"], True)
    ]

    result_step, files = mock_fullstack_agent.execute_step(step)

    assert result_step.status == TaskStatus.COMPLETED
    assert "ATTEMPT 1 FAILED" in result_step.logs
    assert "Passed output" in result_step.logs
    assert "fixed.py" in files
    assert mock_fullstack_agent.response_handler.handle.call_count == 2
