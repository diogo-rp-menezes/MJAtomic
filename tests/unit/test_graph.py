import pytest
from unittest.mock import MagicMock, patch
from src.core.graph.workflow import create_dev_graph, AgentState
from src.core.models import DevelopmentPlan, DevelopmentStep, TaskStatus, AgentRole

# Helper to create dummy steps
def create_step(id, desc):
    return DevelopmentStep(id=id, description=desc, role=AgentRole.FULLSTACK)

@pytest.fixture
def mock_graph_agents():
    with patch("src.core.graph.workflow.TechLeadAgent") as MockTL, \
         patch("src.core.graph.workflow.FullstackAgent") as MockFS, \
         patch("src.core.graph.workflow.CodeReviewAgent") as MockCR:

        # Setup TechLead
        tl_instance = MockTL.return_value
        tl_instance.create_development_plan.return_value = DevelopmentPlan(
            original_request="Test",
            steps=[create_step("1", "Step 1"), create_step("2", "Step 2")]
        )

        # Setup Fullstack
        fs_instance = MockFS.return_value
        def execute_side_effect(step):
            # Return success by default, can be overridden in test
            step.status = TaskStatus.COMPLETED
            return step
        fs_instance.execute_step.side_effect = execute_side_effect

        # Setup Reviewer
        cr_instance = MockCR.return_value
        def review_side_effect(step):
            step.logs = "VERDICT: PASS"
            return step
        cr_instance.review_step.side_effect = review_side_effect

        yield MockTL, MockFS, MockCR

def test_graph_happy_path(mock_graph_agents):
    """Test complete flow with 2 steps passing."""
    app = create_dev_graph()

    inputs = {"project_path": "./test_workspace", "plan": DevelopmentPlan(original_request="Test")}

    # Run the graph
    final_state = app.invoke(inputs)

    assert final_state["current_step_index"] == 2
    assert len(final_state["plan"].steps) == 2
    assert final_state["plan"].steps[0].status == TaskStatus.COMPLETED
    assert final_state["plan"].steps[1].status == TaskStatus.COMPLETED
