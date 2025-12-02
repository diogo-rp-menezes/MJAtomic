import pytest
from unittest.mock import MagicMock, patch
import os
import json
from src.agents.fullstack.agent import FullstackAgent
from src.core.models import DevelopmentStep, TaskStatus

@pytest.fixture
def mock_env_false():
    with patch.dict(os.environ, {"ENABLE_VECTOR_MEMORY": "false"}):
        yield

def test_fullstack_agent_initialization_no_memory(mock_env_false):
    with patch('src.agents.fullstack.agent.VectorMemory') as MockVectorMemory, \
         patch('src.agents.fullstack.agent.CodeIndexer') as MockCodeIndexer, \
         patch('src.agents.fullstack.agent.LLMProvider'), \
         patch('src.agents.fullstack.agent.FileIOTool'), \
         patch('src.agents.fullstack.agent.SecureExecutorTool'):

        agent = FullstackAgent(workspace_path="/tmp/test_workspace")

        # Verify memory is None
        assert agent.memory is None
        # Verify VectorMemory and CodeIndexer were NOT instantiated
        MockVectorMemory.assert_not_called()
        MockCodeIndexer.assert_not_called()

def test_fullstack_agent_execution_creates_file_without_memory(mock_env_false):
    with patch('src.agents.fullstack.agent.VectorMemory') as MockVectorMemory, \
         patch('src.agents.fullstack.agent.CodeIndexer') as MockCodeIndexer, \
         patch('src.agents.fullstack.agent.LLMProvider') as MockLLMProvider, \
         patch('src.agents.fullstack.agent.FileIOTool') as MockFileIOTool, \
         patch('src.agents.fullstack.agent.SecureExecutorTool') as MockSecureExecutorTool:

        # Instantiate agent
        # Note: Patches are active, so the classes used inside __init__ are mocks
        agent = FullstackAgent(workspace_path="/tmp/test_workspace")

        # Verify agent.llm is a mock (instance of the mocked class)
        # agent.llm = LLMProvider(...) -> MockLLMProvider()
        # So we need to configure the instance returned by MockLLMProvider
        mock_llm_instance = agent.llm

        # Configure LLM response
        response_data = {
            "files": [
                {"filename": "hello.py", "content": "print('Hello World')"}
            ],
            "command": "python hello.py"
        }

        # The agent calls generate_response on the LLMProvider instance
        mock_llm_instance.generate_response.return_value = json.dumps(response_data)

        # Configure Executor response
        agent.executor.run_command.return_value = {"exit_code": 0, "output": "Hello World"}

        # Define step
        step = DevelopmentStep(
            id="test-step",
            description="Create hello.py",
            role="FULLSTACK",
            status=TaskStatus.PENDING
        )

        # Execute
        result_step, files = agent.execute_step(step)

        # Verify
        assert result_step.status == TaskStatus.COMPLETED
        assert "hello.py" in files
        agent.file_io.write_file.assert_called_with("hello.py", "print('Hello World')")

        # Verify memory was not used (it is None, so code block skipped)
        assert agent.memory is None
