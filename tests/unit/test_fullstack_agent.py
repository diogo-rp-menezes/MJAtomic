import pytest
from unittest.mock import MagicMock, patch
from src.agents.fullstack.agent import FullstackAgent
from src.core.models import DevelopmentStep, TaskStatus
from langchain_core.messages import AIMessage

@pytest.fixture
def mock_fullstack_agent():
    # Mocking dependencies
    with patch('src.agents.fullstack.agent.LLMProvider'), \
         patch('src.agents.fullstack.agent.create_react_agent') as MockCreateReactAgent, \
         patch('src.agents.fullstack.agent.FullstackAgent._load_prompt_template', return_value="Prompt"):

        # Setup graph mock
        mock_graph = MagicMock()
        MockCreateReactAgent.return_value = mock_graph

        agent = FullstackAgent(workspace_path="/tmp/test_workspace")
        agent.graph_mock = mock_graph # Store for assertion
        return agent

def test_execute_step_success(mock_fullstack_agent):
    step = DevelopmentStep(id="1", description="Task", role="FULLSTACK")

    # Mock graph response with final message
    mock_fullstack_agent.agent_executor.invoke.return_value = {
        "messages": [AIMessage(content="Final Answer")]
    }

    result_step, modified_files = mock_fullstack_agent.execute_step(step, "Input")

    assert result_step.status == TaskStatus.COMPLETED
    assert result_step.logs == "Final Answer"
    assert modified_files == []

def test_execute_step_with_files(mock_fullstack_agent):
    step = DevelopmentStep(id="1", description="Task", role="FULLSTACK")

    # Mock graph response with tool call
    tool_msg = AIMessage(content="I wrote the file.")
    tool_msg.tool_calls = [{'name': 'write_file', 'args': {'filename': 'test.py'}}]

    mock_fullstack_agent.agent_executor.invoke.return_value = {
        "messages": [tool_msg]
    }

    result_step, modified_files = mock_fullstack_agent.execute_step(step, "Input")

    assert result_step.status == TaskStatus.COMPLETED
    assert "test.py" in modified_files

def test_execute_step_failure(mock_fullstack_agent):
    step = DevelopmentStep(id="1", description="Task", role="FULLSTACK")

    # Mock graph crash
    mock_fullstack_agent.agent_executor.invoke.side_effect = Exception("Graph Error")

    result_step, modified_files = mock_fullstack_agent.execute_step(step, "Input")

    assert result_step.status == TaskStatus.FAILED
    assert "Falha crítica" in result_step.result
