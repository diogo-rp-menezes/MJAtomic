import pytest
from unittest.mock import MagicMock, patch
from src.core.models import DevelopmentPlan
from src.services.celery_worker.worker import run_graph_task

@pytest.fixture
def mock_graph_execution():
    with patch("src.services.celery_worker.worker.create_dev_graph") as MockGraph, \
         patch("src.services.celery_worker.worker.get_checkpointer") as MockCheckpoint:

        # Setup Mock Graph
        mock_app = MagicMock()
        MockGraph.return_value = mock_app

        # Setup Mock Checkpointer
        mock_checkpointer_instance = MockCheckpoint.return_value

        yield mock_app, mock_checkpointer_instance

def test_run_graph_task_success(mock_graph_execution):
    """Test that the worker runs the graph and returns a thread_id."""
    mock_app, _ = mock_graph_execution

    # Input
    input_plan = DevelopmentPlan(original_request="Test Task")
    input_dict = input_plan.model_dump()

    # Execute
    thread_id = run_graph_task(input_dict)

    assert isinstance(thread_id, str)
    assert len(thread_id) > 0

    # Verify Graph Invoked
    mock_app.invoke.assert_called_once()

    # Verify arguments passed to invoke
    call_args = mock_app.invoke.call_args
    initial_state = call_args[0][0]
    config = call_args[1]['config']

    assert "plan" in initial_state
    assert initial_state["plan"].original_request == "Test Task"
    assert "project_path" in initial_state
    assert initial_state["project_path"] == "./workspace" # Default
    assert config["configurable"]["thread_id"] == thread_id
