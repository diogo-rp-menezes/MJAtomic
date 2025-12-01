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
    @patch("src.agents.fullstack.agent.SecureExecutorTool")
    @patch("src.agents.fullstack.agent.VectorMemory") # Mock Memory
    @patch("src.agents.fullstack.agent.CodeIndexer") # Mock Indexer
    def test_full_chain_flow(self, mock_indexer, mock_memory, mock_secure_executor, mock_reviewer_llm, mock_tech_base, mock_tech_llm, mock_fullstack_llm):
        """
        Tests the complete chain:
        Tech Lead (Plan) -> Fullstack (Exec Step 1) -> Reviewer (Review Step 1)
        """

        # --- 1. SETUP MOCKS ---

        # Tech Lead Mock
        mock_tech_llm_instance = mock_tech_llm.return_value
        from src.core.models import DevelopmentPlan, DevelopmentStep, AgentRole

        # Tech Lead returns JSON plan
        mock_plan_json = json.dumps({
            "original_request": "Create a TDD plan for math lib",
            "steps": [
                {"id": "1", "description": "Create test_math.py", "role": "FULLSTACK"},
                {"id": "2", "description": "Implement math_lib.py", "role": "FULLSTACK"}
            ]
        })
        mock_tech_llm_instance.generate_response.return_value = mock_plan_json

        # Fullstack Mock
        mock_fullstack_llm_instance = mock_fullstack_llm.return_value
        # Fullstack returns JSON with files and command
        mock_fs_response = json.dumps({
            "files": [{"filename": "test_math.py", "content": "assert True"}],
            "command": "pytest"
        })
        mock_fullstack_llm_instance.generate_response.return_value = mock_fs_response

        # Secure Executor Mock
        mock_executor_instance = mock_secure_executor.return_value
        mock_executor_instance.run_command.return_value = {"exit_code": 0, "output": "Passed"}

        # Reviewer Mock
        mock_reviewer_llm_instance = mock_reviewer_llm.return_value
        mock_verdict = CodeReviewVerdict(verdict=Verdict.PASS, justification="Code looks good.")
        mock_reviewer_llm_instance.generate_response.return_value = mock_verdict.model_dump_json()

        # --- 2. AGENT INITIALIZATION ---
        tech_lead = TechLeadAgent(workspace_path="workspace")
        fullstack = FullstackAgent(workspace_path="workspace")
        # Reviewer needs to mock _load_prompt_template to avoid file reading error in test env
        with patch("src.agents.reviewer.agent.CodeReviewAgent._load_prompt_template", return_value="{task_description}"):
            reviewer = CodeReviewAgent()
            # Re-attach mock llm because we re-instantiated
            reviewer.llm = mock_reviewer_llm_instance

            # --- 3. EXECUTION FLOW ---

            # A. PLAN (Tech Lead)
            print("\n--- 1. Tech Lead Planning ---")
            plan = tech_lead.create_development_plan("Create a TDD plan for math lib", "python")

            assert len(plan.steps) == 2
            assert plan.steps[0].role == AgentRole.FULLSTACK

            # B. STEP 1: EXECUTE (Fullstack)
            print("\n--- 2. Executing Step 1 ---")
            step1 = plan.steps[0]

            step1_result, modified_files = fullstack.execute_step(step1)

            assert step1_result.status == TaskStatus.COMPLETED
            assert "test_math.py" in modified_files

            # C. STEP 1: REVIEW (Reviewer)
            print("\n--- 3. Reviewing Step 1 ---")

            verdict = reviewer.review_code(
                task_description=step1_result.description,
                code_context="def test(): pass",
                execution_logs=step1_result.logs
            )

            assert verdict.verdict == Verdict.PASS
