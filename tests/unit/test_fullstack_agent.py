import pytest
from unittest.mock import MagicMock, patch, mock_open
import yaml
import json
from src.agents.fullstack.agent import FullstackAgent

@pytest.fixture
def mock_fullstack_agent():
    # Mocking dependencies to avoid instantiation errors
    with patch('src.agents.fullstack.agent.LLMProvider'), \
         patch('src.agents.fullstack.agent.FileIOTool'), \
         patch('src.agents.fullstack.agent.SecureExecutorTool'), \
         patch('src.agents.fullstack.agent.VectorMemory'), \
         patch('src.agents.fullstack.agent.CodeIndexer'):
        agent = FullstackAgent(workspace_path="/tmp/test_workspace")
        # Reset file_io mock for specific test usage
        agent.file_io = MagicMock()
        return agent

def test_load_config_valid(mock_fullstack_agent):
    """Test loading a valid YAML config file."""
    yaml_content = "languages:\n  python:\n    test_command: pytest"

    with patch("builtins.open", mock_open(read_data=yaml_content)):
        with patch("os.path.exists", return_value=True):
            config = mock_fullstack_agent._load_config("valid_config.yaml")

    assert config == {"languages": {"python": {"test_command": "pytest"}}}

def test_execute_step_green_phase_success(mock_fullstack_agent):
    # 1. Setup Mock Step for GREEN Phase
    mock_step = MagicMock()
    mock_step.description = "Implement user login function"
    mock_step.status = "PENDING"

    # 2. Setup Mock LLM Response
    llm_response = json.dumps({
        "files": [{"filename": "src/login.py", "content": "def login(): return True"}],
        "command": "pytest tests/test_login.py"
    })
    mock_fullstack_agent.llm.generate_response.return_value = llm_response

    # 3. Setup Mock Executor (Exit Code 0 = Success)
    mock_fullstack_agent.executor.run_command.return_value = {
        "exit_code": 0,
        "output": "1 passed"
    }

    # 4. Execute
    result_step = mock_fullstack_agent.execute_step(mock_step)

    # 5. Assertions
    assert result_step.status == "COMPLETED"
    mock_fullstack_agent.file_io.write_file.assert_called_with("src/login.py", "def login(): return True")
