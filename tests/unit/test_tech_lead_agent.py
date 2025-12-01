import pytest
from unittest.mock import MagicMock, patch
import json
from src.agents.tech_lead.agent import TechLeadAgent
from src.core.models import AgentRole, DevelopmentPlan, DevelopmentStep

@pytest.fixture
def mock_tech_lead_agent():
    # Mocking dependencies to avoid instantiation errors
    # Note: TechLeadAgent imports LLMProvider as LLM, so we patch 'src.agents.tech_lead.agent.LLM'
    with patch('src.agents.tech_lead.agent.LLM'), \
         patch('src.agents.tech_lead.agent.BaseAgent._load_prompt_template', return_value="Prompt"):
        agent = TechLeadAgent(workspace_path="/tmp/test_workspace")
        # Ensure mocks are accessible
        agent.llm = MagicMock()
        return agent

def test_create_development_plan_success(mock_tech_lead_agent):
    """Test create_development_plan generates a DevelopmentPlan with valid steps."""

    # Mock structured output from LLM
    mock_plan = DevelopmentPlan(
        original_request="Create a new feature",
        steps=[
            DevelopmentStep(id="1", description="Setup project", role=AgentRole.FULLSTACK),
            DevelopmentStep(id="2", description="Review code", role=AgentRole.ARCHITECT)
        ]
    )

    # The agent calls llm.generate_response
    mock_tech_lead_agent.llm.generate_response.return_value = mock_plan.model_dump_json()

    # Execute
    plan = mock_tech_lead_agent.create_development_plan("Create a new feature", "python")

    assert isinstance(plan, DevelopmentPlan)
    assert len(plan.steps) == 2
    assert plan.steps[0].description == "Setup project"
    assert plan.steps[0].role == AgentRole.FULLSTACK
    assert plan.steps[1].role == AgentRole.ARCHITECT

def test_create_development_plan_llm_failure(mock_tech_lead_agent):
    """Test handling of LLM failure."""
    # LLM returns garbage
    mock_tech_lead_agent.llm.generate_response.return_value = "Invalid JSON"

    with pytest.raises(ValueError):
        mock_tech_lead_agent.create_development_plan("Do something", "python")

def test_create_development_plan_injects_original_request(mock_tech_lead_agent):
    """Test that original_request is injected if missing from LLM response."""
    # LLM returns JSON without original_request
    steps_dict = {
        "steps": [
            {"id": "1", "description": "Step 1", "role": "FULLSTACK", "status": "PENDING"}
        ]
    }
    mock_tech_lead_agent.llm.generate_response.return_value = json.dumps(steps_dict)

    plan = mock_tech_lead_agent.create_development_plan("My Requirements", "python")

    assert plan.original_request == "My Requirements"
    assert len(plan.steps) == 1
    assert plan.steps[0].description == "Step 1"

def test_create_development_plan_empty_response(mock_tech_lead_agent):
    """Test that empty response raises ValueError."""
    mock_tech_lead_agent.llm.generate_response.return_value = ""

    with pytest.raises(ValueError, match="LLM returned an empty response"):
        mock_tech_lead_agent.create_development_plan("Req", "python")

def test_create_development_plan_empty_json_response(mock_tech_lead_agent):
    """Test that empty JSON object response raises ValueError."""
    mock_tech_lead_agent.llm.generate_response.return_value = "{}"

    with pytest.raises(ValueError, match="LLM returned an empty response"):
        mock_tech_lead_agent.create_development_plan("Req", "python")
