import pytest
from unittest.mock import MagicMock, patch
from src.agents.tech_lead.agent import TechLeadAgent
from src.agents.fullstack.agent import FullstackAgent
from src.agents.reviewer.agent import CodeReviewAgent
from src.core.models import Step, AgentRole, TaskStatus
import json
import os
import shutil

# Mock LLM responses with smarter context handling
def mock_llm_generate_response(prompt, system_message=None, json_mode=False):
    prompt_lower = prompt.lower()
    sys_lower = (system_message or "").lower()

    # 1. Reviewer: Verdict (PRIORITY to prevent misinterpretation)
    if "auditor" in sys_lower or "qa" in sys_lower or "verdict" in sys_lower:
        return "VERDICT: PASS\nCode looks good."

    # 2. Tech Lead: Planning
    if "contexto do projeto" in prompt_lower and "objetivo" in prompt_lower:
        return json.dumps({
            "steps": [
                {"description": "Create test_math.py with failing test for add", "role": "FULLSTACK"},
                {"description": "Implement add in math_lib.py", "role": "FULLSTACK"}
            ]
        })

    # 3. Fullstack: Writing Test (Red)
    elif "test_math.py" in prompt_lower or "fase red" in prompt_lower or "create test_math.py" in prompt_lower:
        return json.dumps({
            "files": [
                {
                    "filename": "test_math.py",
                    "content": "def test_add():\n    from math_lib import add\n    assert add(1, 2) == 3"
                }
            ],
            "command": "pytest test_math.py"
        })

    # 4. Fullstack: Implementing Code (Green)
    elif "math_lib.py" in prompt_lower or "implement add" in prompt_lower:
        return json.dumps({
            "files": [
                {
                    "filename": "math_lib.py",
                    "content": "def add(a, b):\n    return a + b"
                }
            ],
            "command": "pytest test_math.py"
        })

    return "{}"

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
    @patch("src.agents.tech_lead.agent.LLMProvider")
    @patch("src.agents.reviewer.agent.LLMProvider")
    @patch("src.agents.fullstack.agent.SecureExecutorTool")
    @patch("src.agents.fullstack.agent.VectorMemory") # Mock DB/RAG
    @patch("src.agents.fullstack.agent.CodeIndexer")
    def test_full_chain_flow(self, mock_indexer, mock_memory, mock_executor_cls, mock_reviewer_llm, mock_tech_llm, mock_fullstack_llm):
        """
        Tests the complete chain:
        Tech Lead (Plan) -> Fullstack (Exec Step 1) -> Reviewer (Review Step 1) -> Fullstack (Exec Step 2) -> Reviewer (Review Step 2)
        """

        # --- 1. SETUP MOCKS ---

        # Mock LLM generation for all agents
        # We use a shared side_effect or assign specific return values if agents use different instances
        # Since we patch the class, we need to configure the instances returned

        mock_tech_llm_instance = mock_tech_llm.return_value
        mock_tech_llm_instance.generate_response.side_effect = mock_llm_generate_response

        mock_fullstack_llm_instance = mock_fullstack_llm.return_value
        mock_fullstack_llm_instance.generate_response.side_effect = mock_llm_generate_response

        mock_reviewer_llm_instance = mock_reviewer_llm.return_value
        mock_reviewer_llm_instance.generate_response.side_effect = mock_llm_generate_response

        # Mock Executor (Docker)
        mock_executor_instance = mock_executor_cls.return_value
        # Sequence of execution results:
        # 1. Step 1 (Red): Expect failure (exit 1) -> Fullstack treats as Success
        # 2. Step 2 (Green): Expect success (exit 0) -> Fullstack treats as Success
        mock_executor_instance.run_command.side_effect = [
            {"exit_code": 1, "output": "ImportError: cannot import name 'add'"}, # Step 1 Attempt 1 (Fail)
            {"exit_code": 0, "output": "1 passed in 0.01s"},                     # Step 1 Attempt 2 (Success)
            {"exit_code": 0, "output": "1 passed in 0.01s"}                      # Step 2 Attempt 1 (Success)
        ]

        # --- 2. AGENT INITIALIZATION ---
        tech_lead = TechLeadAgent(workspace_path="workspace")
        fullstack = FullstackAgent(workspace_path="workspace")
        reviewer = CodeReviewAgent(workspace_path="workspace")

        # --- 3. EXECUTION FLOW ---

        # A. PLAN (Tech Lead)
        print("\n--- 1. Tech Lead Planning ---")
        plan = tech_lead.plan_task("Create a TDD plan for math lib")

        assert len(plan.steps) == 2
        assert plan.steps[0].role == AgentRole.FULLSTACK
        assert "test_math.py" in plan.steps[0].description

        # B. STEP 1: RED PHASE (Fullstack + Reviewer)
        print("\n--- 2. Executing Step 1 (Red) ---")
        step1 = plan.steps[0]
        step1 = fullstack.execute_step(step1)

        assert step1.status == TaskStatus.COMPLETED
        assert "test_math.py" in step1.logs or "Success" in step1.result

        print("\n--- 3. Reviewing Step 1 ---")
        # Simulate logs containing file info for reviewer
        step1.logs += "\nArquivos gerados: ['test_math.py']"
        step1 = reviewer.review_step(step1)

        assert "VERDICT: PASS" in step1.logs

        # C. STEP 2: GREEN PHASE (Fullstack + Reviewer)
        print("\n--- 4. Executing Step 2 (Green) ---")
        step2 = plan.steps[1]
        step2 = fullstack.execute_step(step2)

        assert step2.status == TaskStatus.COMPLETED

        print("\n--- 5. Reviewing Step 2 ---")
        step2.logs += "\nArquivos gerados: ['math_lib.py']"
        step2 = reviewer.review_step(step2)

        assert "VERDICT: PASS" in step2.logs
