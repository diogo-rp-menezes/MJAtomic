import pytest
from unittest.mock import MagicMock, patch, mock_open
import json
from src.agents.fullstack.agent import FullstackAgent
from src.core.models import DevelopmentStep, TaskStatus

@pytest.fixture
def mock_fullstack_agent():
    with patch('src.agents.fullstack.agent.LLMProvider'), \
         patch('src.agents.fullstack.agent.FileIOTool'), \
         patch('src.agents.fullstack.agent.SecureExecutorTool'), \
         patch('src.agents.fullstack.agent.VectorMemory'), \
         patch('src.agents.fullstack.agent.CodeIndexer'):
        agent = FullstackAgent(workspace_path="/tmp/test_workspace")
        agent.llm = MagicMock()
        agent.file_io = MagicMock()
        agent.executor = MagicMock()
        return agent

def test_parse_and_save_files_valid(mock_fullstack_agent):
    """Test parsing a valid response dict with multiple files."""
    data = {
        "files": [
            {"filename": "src/main.py", "content": "print('hello')"},
            {"filename": "README.md", "content": "# Project"}
        ],
        "command": "pytest"
    }

    created = mock_fullstack_agent._parse_and_save_files(data)

    assert len(created) == 2
    assert "src/main.py" in created
    assert "README.md" in created

    # Verify write_file calls
    mock_fullstack_agent.file_io.write_file.assert_any_call("src/main.py", "print('hello')")
    mock_fullstack_agent.file_io.write_file.assert_any_call("README.md", "# Project")

def test_parse_and_save_files_invalid_structure(mock_fullstack_agent):
    """Test handling invalid file list structure."""
    data = {"files": "invalid_string"}
    created = mock_fullstack_agent._parse_and_save_files(data)
    assert created == []
    mock_fullstack_agent.file_io.write_file.assert_not_called()

def test_execute_step_success(mock_fullstack_agent):
    """Test execute_step successful run returning tuple."""
    step = DevelopmentStep(id="1", description="Implement feature", role="FULLSTACK")

    # Mock LLM Response
    mock_response = json.dumps({
        "files": [{"filename": "main.py", "content": "code"}],
        "command": "python main.py"
    })
    mock_fullstack_agent.llm.generate_response.return_value = mock_response

    # Mock Executor Success
    mock_fullstack_agent.executor.run_command.return_value = {
        "exit_code": 0,
        "output": "Success"
    }

    result_step, files = mock_fullstack_agent.execute_step(step)

    assert result_step.status == TaskStatus.COMPLETED
    assert "Success" in result_step.logs
    assert files == ["main.py"]
    mock_fullstack_agent.file_io.write_file.assert_called_with("main.py", "code")

def test_execute_step_retry_logic(mock_fullstack_agent):
    """Test self-healing retry logic."""
    step = DevelopmentStep(id="1", description="Implement feature", role="FULLSTACK")

    # Attempt 1: Fail
    response_fail = json.dumps({"files": [], "command": "fail_cmd"})
    # Attempt 2: Success
    response_success = json.dumps({
        "files": [{"filename": "fixed.py", "content": "fixed"}],
        "command": "success_cmd"
    })

    mock_fullstack_agent.llm.generate_response.side_effect = [response_fail, response_success]

    mock_fullstack_agent.executor.run_command.side_effect = [
        {"exit_code": 1, "output": "Error"},
        {"exit_code": 0, "output": "Passed"}
    ]

    result_step, files = mock_fullstack_agent.execute_step(step)

    assert result_step.status == TaskStatus.COMPLETED
    assert "ATTEMPT 1 FAILED" in result_step.logs  # Should see attempt 1 in logs
    assert "Passed" in result_step.logs
    assert "fixed.py" in files
