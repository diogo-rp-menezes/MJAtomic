import pytest
from unittest.mock import MagicMock, patch
from src.core.graph.workflow import create_dev_graph, AgentState
from src.core.models import DevelopmentPlan, DevelopmentStep, TaskStatus, AgentRole, Verdict

@pytest.fixture
def mock_graph_agents():
    with patch("src.core.graph.workflow.TechLeadAgent") as MockTL, \
         patch("src.core.graph.workflow.FullstackAgent") as MockFS, \
         patch("src.core.graph.workflow.CodeReviewAgent") as MockCR:

        # Setup TechLead
        tl_instance = MockTL.return_value
        tl_instance.plan_task.return_value = DevelopmentPlan(
            original_request="Test",
            steps=[
                DevelopmentStep(id="1", description="Step 1", role=AgentRole.FULLSTACK),
                DevelopmentStep(id="2", description="Step 2", role=AgentRole.FULLSTACK)
            ]
        )

        # Setup Fullstack
        fs_instance = MockFS.return_value
        def execute_side_effect(step, task_input):
            # Return tuple (step, modified_files)
            step.status = TaskStatus.COMPLETED
            return step, []
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

    final_state = app.invoke(inputs)

    assert final_state["current_step_index"] == 2
    assert len(final_state["plan"].steps) == 2
    assert final_state["plan"].steps[0].status == TaskStatus.COMPLETED
    assert final_state["plan"].steps[1].status == TaskStatus.COMPLETED

def test_graph_retry_logic(mock_graph_agents):
    """Test flow where step 1 fails once then passes."""
    _, MockFS, MockCR = mock_graph_agents

    # Reviewer side effect to simulate failure then pass
    cr_instance = MockCR.return_value

    # We use a mutable object to track calls because side_effect iterator is safer
    # But here we need logic based on which step is being reviewed or retry count.
    # The reviewer receives `step`.

    # Let's verify that retry logic works if VERDICT is FAIL.

    call_count = 0
    def review_logic(step):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            step.logs = "VERDICT: FAIL"
        else:
            step.logs = "VERDICT: PASS"
        return step

    cr_instance.review_step.side_effect = review_logic

    app = create_dev_graph()
    inputs = {"project_path": "./test_workspace", "plan": DevelopmentPlan(original_request="Test")}

    final_state = app.invoke(inputs)

    # Should have retried step 1
    assert call_count >= 3 # Fail S1, Pass S1, Pass S2
    assert final_state["plan"].steps[0].status == TaskStatus.COMPLETED
