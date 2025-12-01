import pytest
from unittest.mock import MagicMock, patch
from src.agents.tech_lead.agent import TechLeadAgent
from src.agents.fullstack.agent import FullstackAgent
from src.agents.reviewer.agent import CodeReviewAgent
from src.core.models import DevelopmentStep, AgentRole, TaskStatus, Verdict, CodeReviewVerdict
import json
import os
import shutil

class TestIntegration:

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        # Setup: Ensure workspace exists
        os.makedirs("workspace", exist_ok=True)
        yield
        # Teardown: Clean workspace
        if os.path.exists("workspace"):
            shutil.rmtree("workspace")

    @patch("src.agents.fullstack.agent.LLMProvider")
    @patch("src.agents.tech_lead.agent.LLM")
    @patch("src.agents.tech_lead.agent.BaseAgent._load_prompt_template", return_value="Prompt")
    @patch("src.agents.reviewer.agent.LLMProvider")
    @patch("src.agents.fullstack.agent.create_react_agent")
    @patch("src.agents.fullstack.agent.AgentExecutor")
    def test_full_chain_flow(self, mock_agent_executor, mock_create_react_agent, mock_reviewer_llm, mock_tech_base, mock_tech_llm, mock_fullstack_llm):
        """
        Tests the complete chain:
        Tech Lead (Plan) -> Fullstack (Exec Step 1) -> Reviewer (Review Step 1)
        """

        # --- 1. SETUP MOCKS ---

        # Tech Lead Mock
        mock_tech_llm_instance = mock_tech_llm.return_value
        from src.core.models import DevelopmentPlan, DevelopmentStep, AgentRole

        mock_plan = DevelopmentPlan(
            original_request="Create a TDD plan for math lib",
            steps=[
                DevelopmentStep(id="s1", description="Create test_math.py with failing test for add", role=AgentRole.FULLSTACK),
                DevelopmentStep(id="s2", description="Implement add in math_lib.py", role=AgentRole.FULLSTACK)
            ]
        )
        mock_tech_llm_instance.generate_response.return_value = mock_plan.model_dump_json()

        # Fullstack Mock (Agent Executor)
        mock_executor_instance = mock_agent_executor.return_value
        # Intermediate steps for Step 1 (simulate write_file)
        mock_tool_call = MagicMock()
        mock_tool_call.tool = "write_file"
        mock_tool_call.tool_input = {"filename": "test_math.py"}

        mock_executor_instance.invoke.return_value = {
            "output": "Created test_math.py",
            "intermediate_steps": [(mock_tool_call, "File written")]
        }

        # Reviewer Mock
        mock_reviewer_llm_instance = mock_reviewer_llm.return_value
        mock_verdict = CodeReviewVerdict(verdict=Verdict.PASS, justification="Code looks good.")
        mock_reviewer_llm_instance.generate_response.return_value = mock_verdict.model_dump_json()

        # --- 2. AGENT INITIALIZATION ---
        tech_lead = TechLeadAgent(workspace_path="workspace")
        fullstack = FullstackAgent(workspace_path="workspace")
        reviewer = CodeReviewAgent()

        # --- 3. EXECUTION FLOW ---

        # A. PLAN (Tech Lead)
        print("\n--- 1. Tech Lead Planning ---")
        plan = tech_lead.create_development_plan("Create a TDD plan for math lib", "python")

        assert len(plan.steps) == 2
        assert plan.steps[0].role == AgentRole.FULLSTACK

        # B. STEP 1: EXECUTE (Fullstack)
        print("\n--- 2. Executing Step 1 ---")
        step1 = plan.steps[0]
        # We mock file writing via the executor response, so we don't need real files for this test logic check
        # But Reviewer needs content. We should patch read_file for reviewer.

        step1_result, modified_files = fullstack.execute_step(step1)

        assert step1_result.status == TaskStatus.COMPLETED
        assert "test_math.py" in modified_files

        # C. STEP 1: REVIEW (Reviewer)
        print("\n--- 3. Reviewing Step 1 ---")
        # We need to mock file reading inside reviewer
        with patch("src.agents.reviewer.agent.CodeReviewAgent._load_prompt_template", return_value="{task_description}"):
            # Re-init because we patched _load_prompt_template on class
            reviewer = CodeReviewAgent()
            # Mock LLM on this new instance
            reviewer.llm.generate_response.return_value = mock_verdict.model_dump_json()

            verdict = reviewer.review_code(
                task_description=step1_result.description,
                code_context="def test(): pass",
                execution_logs=step1_result.logs
            )

        assert verdict.verdict == Verdict.PASS
