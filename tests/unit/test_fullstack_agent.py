import pytest
from unittest.mock import MagicMock, patch
from src.agents.fullstack.agent import FullstackAgent
from src.core.models import DevelopmentStep, TaskStatus

# We patch the imports used by the class under test
@pytest.fixture
def mock_fullstack_agent():
    with patch('src.agents.fullstack.agent.LLMProvider'), \
         patch('src.agents.fullstack.agent.create_react_agent'), \
         patch('src.agents.fullstack.agent.AgentExecutor') as MockAgentExecutor:

        agent = FullstackAgent(workspace_path="/tmp/test_workspace")
        agent.agent_executor = MockAgentExecutor.return_value
        return agent

def test_execute_step_success(mock_fullstack_agent):
    """
    Test execute_step when the agent executor succeeds.
    """
    # 1. Setup Mock Step
    mock_step = DevelopmentStep(
        id="1",
        description="Write a hello world script",
        role="FULLSTACK",
        status=TaskStatus.PENDING
    )

    # 2. Setup AgentExecutor Response
    mock_fullstack_agent.agent_executor.invoke.return_value = {
        "output": "I have created the file hello.py and verified it."
    }

    # 3. Execute
    result_step = mock_fullstack_agent.execute_step(mock_step)

    # 4. Assertions
    assert result_step.status == TaskStatus.COMPLETED
    assert result_step.result == "Tarefa concluída com sucesso."
    assert "I have created the file" in result_step.logs

    # Verify invoke was called with the correct input
    mock_fullstack_agent.agent_executor.invoke.assert_called_once()
    call_args = mock_fullstack_agent.agent_executor.invoke.call_args[0][0]
    assert "Write a hello world script" in call_args["input"]

def test_execute_step_failure(mock_fullstack_agent):
    """
    Test execute_step when the agent executor raises an exception.
    """
    # 1. Setup Mock Step
    mock_step = DevelopmentStep(
        id="2",
        description="Crash the system",
        role="FULLSTACK",
        status=TaskStatus.PENDING
    )

    # 2. Setup AgentExecutor Exception
    mock_fullstack_agent.agent_executor.invoke.side_effect = Exception("API Timeout")

    # 3. Execute
    result_step = mock_fullstack_agent.execute_step(mock_step)

    # 4. Assertions
    assert result_step.status == TaskStatus.FAILED
    assert "Falha crítica" in result_step.result
    assert "API Timeout" in result_step.result
