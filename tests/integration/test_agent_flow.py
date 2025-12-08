import pytest
from unittest.mock import MagicMock, patch
import os
from src.core.factory import AgentFactory
from src.core.models import AgentRole, DevelopmentStep, TaskStatus
from src.core.config import settings # Import the singleton

class TestAgentFlow:
    @pytest.fixture(autouse=True)
    def mock_settings(self):
        # Patch the configuration singleton to force local provider
        # We use a context manager to ensure it reverts after test
        with patch.object(settings, 'LLM_PROVIDER', 'local'), \
             patch.object(settings, 'FULLSTACK_MODEL', 'dummy'), \
             patch.object(settings, 'FULLSTACK_BASE_URL', 'http://dummy'), \
             patch.object(settings, 'OLLAMA_BASE_URL', 'http://dummy'), \
             patch.object(settings, 'LOCAL_LLM_API_KEY', 'dummy'), \
             patch.dict(os.environ, {"ENABLE_VECTOR_MEMORY": "false"}):
            yield

    @patch('src.core.factory.SecureExecutorTool')
    @patch('src.core.llm.provider.LLMProvider.generate_response')
    def test_fullstack_flow(self, mock_generate, mock_executor_cls):
        """
        Integration test verifying:
        Factory -> Agent -> PromptBuilder -> LLM -> ResponseHandler -> Executor
        """
        # 1. Setup Executor Mock instance
        mock_executor = mock_executor_cls.return_value
        # ResponseHandler calls executor.run_command for standard shell commands
        mock_executor.run_command.return_value = {"success": True, "output": "Echoed test"}

        # 2. Setup LLM Mock response
        # Returning a valid JSON that FullstackAgent logic (and components) can process
        mock_generate.return_value = '{"command": "echo test", "files": []}'

        # 3. Create Agent via Factory
        # This exercises the Factory logic and Component wiring
        # The mock_settings fixture ensures LLMProvider is initialized as 'local', avoiding Google Auth
        agent = AgentFactory.create_agent(AgentRole.FULLSTACK, project_path="/tmp/test_flow")

        # 4. Create and Execute Step
        step = DevelopmentStep(id="1", description="Test Flow", role="FULLSTACK")
        result_step, files = agent.execute_step(step)

        # 5. Assertions
        # Check if status updated to COMPLETED (means loop finished successfully)
        assert result_step.status == TaskStatus.COMPLETED

        # Check if result contains success message
        assert "Success" in result_step.result or "Echoed test" in result_step.logs

        # Verify the chain of calls
        mock_generate.assert_called() # LLM was invoked
        mock_executor.run_command.assert_called_with("echo test") # ResponseHandler parsed and called Executor
