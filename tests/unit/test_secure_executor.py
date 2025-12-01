import pytest
from unittest.mock import patch, MagicMock
from src.tools.secure_executor import SecureExecutorTool

@patch("src.tools.secure_executor.docker.from_env")
def test_run_command_success(mock_docker):
    mock_client = MagicMock()
    mock_docker.return_value = mock_client
    mock_container = MagicMock()
    mock_client.containers.run.return_value = mock_container

    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.return_value = b"Output"

    executor = SecureExecutorTool(workspace_path="/tmp")
    result = executor.run_command("echo hi")

    assert result["success"] is True
    assert result["output"] == "Output"
    mock_client.containers.run.assert_called_once()

@patch("src.tools.secure_executor.docker.from_env")
def test_run_command_failure(mock_docker):
    mock_client = MagicMock()
    mock_docker.return_value = mock_client
    mock_container = MagicMock()
    mock_client.containers.run.return_value = mock_container

    mock_container.wait.return_value = {"StatusCode": 1}
    mock_container.logs.return_value = b"Error"

    executor = SecureExecutorTool(workspace_path="/tmp")
    result = executor.run_command("bad cmd")

    assert result["success"] is False
    assert result["exit_code"] == 1
