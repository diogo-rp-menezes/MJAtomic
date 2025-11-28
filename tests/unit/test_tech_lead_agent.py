import pytest
from unittest.mock import MagicMock, patch
import json
from src.agents.tech_lead.agent import TechLeadAgent
from src.core.models import AgentRole, DevelopmentPlan

@pytest.fixture
def mock_tech_lead_agent():
    # Mocking dependencies to avoid instantiation errors
    with patch('src.agents.tech_lead.agent.LLMProvider'), \
         patch('src.agents.tech_lead.agent.FileIOTool'):
        agent = TechLeadAgent(workspace_path="/tmp/test_workspace")
        # Ensure mocks are accessible
        agent.llm_provider = MagicMock()
        agent.file_io = MagicMock()
        return agent

def test_parse_with_retry_valid_object(mock_tech_lead_agent):
    """Test parsing a valid JSON object with 'steps' key."""
    json_text = json.dumps({
        "steps": [
            {"description": "Step 1", "role": "FULLSTACK"},
            {"description": "Step 2", "role": "REVIEWER"}
        ]
    })

    parsed = mock_tech_lead_agent._parse_with_retry(json_text)

    assert len(parsed) == 2
    assert parsed[0]["description"] == "Step 1"
    assert parsed[1]["role"] == "REVIEWER"

def test_plan_task_success(mock_tech_lead_agent):
    """Test plan_task generates a DevelopmentPlan with valid steps."""
    # Mock LLM Response
    mock_response = json.dumps({
        "steps": [
            {"description": "Setup project", "role": "FULLSTACK"},
            {"description": "Review code", "role": "REVIEWER"}
        ]
    })
    mock_tech_lead_agent.llm_provider.generate_response.return_value = mock_response

    # Mock FileIO
    mock_tech_lead_agent.file_io.get_project_structure.return_value = "- src/"

    # Execute
    plan = mock_tech_lead_agent.plan_task("Create a new feature")

    assert isinstance(plan, DevelopmentPlan)
    assert len(plan.steps) == 2
    assert plan.steps[0].description == "Setup project"
    assert plan.steps[0].role == AgentRole.FULLSTACK
    assert plan.steps[1].role == AgentRole.REVIEWER # Actually maps to AgentRole (Enum)
