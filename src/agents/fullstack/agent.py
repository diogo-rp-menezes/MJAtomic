import logging
from typing import Tuple, List
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from src.core.models import DevelopmentStep, TaskStatus
from src.core.llm.provider import LLMProvider
from src.tools.core_tools import core_tools

class FullstackAgent:
    def __init__(self,
                 workspace_path: str = "./workspace",
                 llm_provider: LLMProvider = None):

        self.workspace_path = workspace_path
        self.logger = logging.getLogger(self.__class__.__name__)
        self.llm = llm_provider or LLMProvider(profile="smart")

        # 1. Carregar o template do prompt
        system_prompt = self._load_prompt_template("src/agents/fullstack/prompt.md")

        # 2. Criar o Agente ReAct com LangGraph
        self.agent_executor = create_react_agent(self.llm.get_llm(), core_tools, state_modifier=system_prompt)

    def _load_prompt_template(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Erro ao carregar o prompt {file_path}: {e}")
            raise

    def execute_step(self, step: DevelopmentStep, task_input: str) -> Tuple[DevelopmentStep, List[str]]:
        self.logger.info(f"🤖 [Fullstack] Executando: {step.description}")
        step.status = TaskStatus.IN_PROGRESS
        modified_files = []

        try:
            # Invoca o grafo
            # LangGraph espera um dict com "messages"
            inputs = {"messages": [HumanMessage(content=task_input)]}

            # invoke retorna o estado final
            final_state = self.agent_executor.invoke(inputs)

            messages = final_state.get("messages", [])

            # Extração de arquivos modificados e resposta final
            final_answer = ""
            if messages:
                final_answer = messages[-1].content

                # Iterar para achar chamadas de ferramenta write_file
                for msg in messages:
                    if hasattr(msg, 'tool_calls'):
                        for tool_call in msg.tool_calls:
                            if tool_call['name'] == 'write_file':
                                args = tool_call['args']
                                if 'filename' in args:
                                    modified_files.append(args['filename'])

            step.status = TaskStatus.COMPLETED
            step.result = "Tarefa concluída com sucesso."
            step.logs = str(final_answer)
            self.logger.info(f"✅ [Fullstack] Concluído: {step.description}")

        except Exception as e:
            self.logger.error(f"❌ [Fullstack] Erro ao executar o passo: {e}")
            step.status = TaskStatus.FAILED
            step.result = f"Falha crítica durante a execução do agente: {str(e)}"

        return step, list(set(modified_files))
