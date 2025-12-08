import os
import logging
from src.core.models import AgentRole
from src.core.config import settings
from src.core.llm.provider import LLMProvider
from src.tools.file_io import FileIOTool
from src.tools.secure_executor import SecureExecutorTool
from src.core.memory.vector_store import VectorMemory
from src.core.memory.indexer import CodeIndexer

# Agents
from src.agents.tech_lead.agent import TechLeadAgent
from src.agents.fullstack.agent import FullstackAgent
from src.agents.fullstack.components import PromptBuilder, ResponseHandler

logger = logging.getLogger(__name__)

class AgentFactory:
    @staticmethod
    def create_agent(role: AgentRole, project_path: str = "./workspace"):
        """
        Factory method to create agents with fully injected dependencies.
        """
        if role == AgentRole.TECH_LEAD:
            # TechLead Config
            model_name = settings.TECH_LEAD_MODEL
            # Force Google (base_url=None) unless specifically needed otherwise
            llm = LLMProvider(model_name=model_name, base_url=None)

            return TechLeadAgent(llm=llm, workspace_path=project_path)

        elif role == AgentRole.FULLSTACK:
            # Fullstack Config
            model_name = settings.FULLSTACK_MODEL
            base_url = settings.FULLSTACK_BASE_URL
            llm = LLMProvider(model_name=model_name, base_url=base_url)

            # Tools
            file_io = FileIOTool(root_path=project_path)
            executor = SecureExecutorTool(workspace_path=project_path)

            # Memory Wiring (moved from Agent to Factory)
            memory = None
            indexer = None
            if os.getenv("ENABLE_VECTOR_MEMORY", "true").lower() == "true":
                try:
                    memory = VectorMemory()
                    indexer = CodeIndexer(workspace_path=project_path)
                    logger.info("Vector Memory initialized in Factory.")
                except Exception as e:
                    logger.error(f"Failed to initialize Vector Memory in Factory: {e}")

            # Components
            prompt_builder = PromptBuilder(memory=memory, indexer=indexer)
            response_handler = ResponseHandler(file_system=file_io, executor=executor)

            return FullstackAgent(
                llm=llm,
                prompt_builder=prompt_builder,
                response_handler=response_handler,
                workspace_path=project_path
            )

        else:
            raise NotImplementedError(f"Factory support for role {role} is not yet implemented.")
