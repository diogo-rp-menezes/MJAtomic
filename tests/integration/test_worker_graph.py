import pytest
from unittest.mock import MagicMock, patch
import json
from src.core.models import DevelopmentPlan, DevelopmentStep, TaskStatus, AgentRole
from src.services.celery_worker.worker import run_agent_graph

@pytest.fixture
def mock_graph_execution():
    with patch("src.services.celery_worker.worker.create_dev_graph") as MockGraph, \
         patch("src.services.celery_worker.worker.TaskRepository") as MockRepo, \
         patch("src.services.celery_worker.worker.SessionLocal"):

        # Setup Mock Graph
        mock_app = MagicMock()
        MockGraph.return_value = mock_app

        # Setup Mock DB Repo
        mock_repo_instance = MockRepo.return_value

        yield mock_app, mock_repo_instance

def test_run_agent_graph_success(mock_graph_execution):
    """Test that the worker runs the graph and updates DB."""
    mock_app, mock_repo = mock_graph_execution

    # Mock streaming events
    plan_step_1 = DevelopmentPlan(original_request="Test", steps=[
        DevelopmentStep(id="s1", description="Task 1", role=AgentRole.FULLSTACK, status=TaskStatus.COMPLETED)
    ])

    # Simulate 2 events: Planner done, Executor done
    mock_app.stream.return_value = [
        {"planner": {"plan": plan_step_1}},
        {"executor": {"plan": plan_step_1}}
    ]

    # Input
    input_plan = DevelopmentPlan(original_request="Test", steps=[
        DevelopmentStep(id="s1", description="Task 1", role=AgentRole.FULLSTACK)
    ])

    # Execute
    result = run_agent_graph(input_plan.model_dump_json(), "./workspace")

    assert result == "Graph Execution Completed"

    # Verify DB Sync called
    assert mock_repo.update_step.call_count >= 2
    mock_repo.update_step.assert_called_with("s1", TaskStatus.COMPLETED, "", "")

def test_run_agent_graph_exception(mock_graph_execution):
    """Test worker resilience to graph errors."""
    mock_app, _ = mock_graph_execution

    mock_app.stream.side_effect = Exception("Graph Crash")

    input_plan = DevelopmentPlan(original_request="Test")
    result = run_agent_graph(input_plan.model_dump_json(), "./workspace")

    assert "Error: Graph Crash" in result
