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
            DevelopmentStep(id="2", description="Review code", role=AgentRole.REVIEWER)
        ]
    )

    # The agent calls llm.generate_response which now returns the object directly
    mock_tech_lead_agent.llm.generate_response.return_value = mock_plan

    # Execute
    plan = mock_tech_lead_agent.create_development_plan("Create a new feature", "python")

    assert isinstance(plan, DevelopmentPlan)
    assert len(plan.steps) == 2
    assert plan.steps[0].description == "Setup project"
    assert plan.steps[0].role == AgentRole.FULLSTACK
    assert plan.steps[1].role == AgentRole.REVIEWER

def test_create_development_plan_llm_failure(mock_tech_lead_agent):
    """Test handling of LLM failure."""
    # LLM raises exception
    mock_tech_lead_agent.llm.generate_response.side_effect = ValueError("LLM Error")

    with pytest.raises(ValueError):
        mock_tech_lead_agent.create_development_plan("Do something", "python")

def test_create_development_plan_recovery(mock_tech_lead_agent):
    """Test recovery when LLM returns DevelopmentPlan missing original_request."""
    # LLM returns valid object but missing original_request
    mock_plan = DevelopmentPlan(
        original_request="", # Empty
        steps=[]
    )
    mock_tech_lead_agent.llm.generate_response.return_value = mock_plan

    # Execute
    requirements = "My Requirements"
    plan = mock_tech_lead_agent.create_development_plan(requirements, "python")

    # Assert that the agent filled in the missing request
    assert plan.original_request == requirements
