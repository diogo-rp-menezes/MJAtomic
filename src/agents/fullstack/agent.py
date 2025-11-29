import logging
from typing import Tuple, List
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from src.core.models import DevelopmentStep, TaskStatus
from src.core.llm.provider import LLMProvider
from src.tools.core_tools import core_tools # Importa a lista de ferramentas

class FullstackAgent:
    def __init__(self,
                 workspace_path: str = "./workspace",
                 llm_provider: LLMProvider = None):

        self.workspace_path = workspace_path
        self.logger = logging.getLogger(self.__class__.__name__)
        self.llm = llm_provider or LLMProvider(profile="smart") # Usar o perfil 'smart' para raciocínio

        # 1. Carregar o template do prompt
        prompt_template = self._load_prompt_template("src/agents/fullstack/prompt.md")
        prompt = PromptTemplate.from_template(prompt_template)

        # 2. Criar o Agente ReAct (Reasoning and Acting)
        # Este agente é o "cérebro" que decide qual ferramenta usar.
        agent = create_react_agent(self.llm.get_llm(), core_tools, prompt)

        # 3. Criar o Executor do Agente
        # Este é o "runtime" que executa o loop de pensamento e ação do agente.
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=core_tools,
            verbose=True,  # verbose=True é ótimo para debugar o pensamento do agente
            handle_parsing_errors=True, # Lida com erros de formatação do LLM
            max_iterations=10, # Previne loops infinitos
            return_intermediate_steps=True # Retorna os passos intermediários para auditoria
        )

    def _load_prompt_template(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Erro ao carregar o prompt {file_path}: {e}")
            raise

    def execute_step(self, step: DevelopmentStep) -> Tuple[DevelopmentStep, List[str]]:
        self.logger.info(f"🤖 [Fullstack] Executando: {step.description}")
        step.status = TaskStatus.IN_PROGRESS
        modified_files = []

        try:
            # A mágica acontece aqui. Delegamos toda a complexidade para o AgentExecutor.
            # O agente usará as ferramentas (ler, escrever, executar) quantas vezes
            # forem necessárias até que a tarefa seja concluída.
            task_input = f"Complete a seguinte tarefa de desenvolvimento: {step.description}"

            response = self.agent_executor.invoke({
                "input": task_input
            })

            # Extração de arquivos modificados
            if "intermediate_steps" in response:
                for action, observation in response["intermediate_steps"]:
                    if action.tool == "write_file":
                        # action.tool_input pode ser um dict ou string dependendo do modelo/parser
                        # Se for string, pode precisar de parse, mas o padrão langchain costuma dar o input estruturado se possível
                        # Mas write_file aceita string "filename, content".
                        # O react agent output parser geralmente coloca tool_input como string ou dict.

                        tool_input = action.tool_input
                        filename = None

                        if isinstance(tool_input, dict) and "filename" in tool_input:
                            filename = tool_input["filename"]
                        elif isinstance(tool_input, str):
                            # Se for string, tentamos inferir. Mas write_file no core_tools é @tool func.
                            # LangChain às vezes passa argumentos como string posicional ou json string.
                            # Para simplificar, assumimos que se o agente usou corretamente, teremos o filename.
                            # Se não conseguirmos extrair fácil, seguimos.
                            # Mas a ferramenta write_file tem signature (filename, content).
                            pass

                        if filename:
                            modified_files.append(filename)

            # O resultado final do agente é a sua resposta em linguagem natural.
            final_answer = response.get("output", "Nenhuma resposta final produzida.")

            step.status = TaskStatus.COMPLETED
            step.result = "Tarefa concluída com sucesso."
            step.logs = final_answer # Armazena o raciocínio final do agente
            self.logger.info(f"✅ [Fullstack] Concluído: {step.description}")

        except Exception as e:
            self.logger.error(f"❌ [Fullstack] Erro ao executar o passo: {e}")
            step.status = TaskStatus.FAILED
            step.result = f"Falha crítica durante a execução do agente: {str(e)}"

        return step, list(set(modified_files))
