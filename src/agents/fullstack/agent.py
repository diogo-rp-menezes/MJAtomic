from src.core.models import Step, TaskStatus
from src.core.llm.provider import LLMProvider
from src.core.memory.vector_store import VectorMemory
from src.core.memory.indexer import CodeIndexer
from src.tools.file_io import FileIOTool
from src.tools.secure_executor import SecureExecutorTool
from src.core.logger import logger
from src.core.config import settings
import os
import yaml
import json
from typing import Tuple, List

class FullstackAgent:
    def __init__(self,
                 workspace_path: str = "./workspace",
                 llm_provider: LLMProvider = None,
                 file_io: FileIOTool = None,
                 executor: SecureExecutorTool = None,
                 memory = None,
                 indexer = None):

        self.workspace_path = workspace_path

        model_name = settings.FULLSTACK_MODEL

        # Allow Fullstack to have its own Base URL if using local provider,
        # otherwise defaults to None (letting LLMProvider decide based on global env)
        base_url = settings.FULLSTACK_BASE_URL

        self.llm = llm_provider or LLMProvider(model_name=model_name, base_url=base_url)
        self.file_io = file_io or FileIOTool(root_path=self.workspace_path)
        self.executor = executor or SecureExecutorTool(workspace_path=self.workspace_path)
        self.memory = memory
        self.indexer = indexer

        # Carrega config se existir
        self.config = self._load_config(os.path.join(workspace_path, "config.yaml"))

        # Lazy Load de memória se não injetado e não falhar
        if self.memory is None:
            if os.getenv("ENABLE_VECTOR_MEMORY", "true").lower() == "true":
                try:
                    self.memory = VectorMemory()
                    self.indexer = CodeIndexer(workspace_path=self.workspace_path)
                    logger.info("Vector Memory ativada.")
                except Exception as e:
                    logger.error(f"Falha ao inicializar a Vector Memory, continuando em modo degradado: {e}")
            else:
                logger.warning("Vector Memory desativada por configuração.")

    def _load_config(self, path: str) -> dict:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f: return yaml.safe_load(f)
            except: pass
        return {}

    def _parse_and_save_files(self, data: dict) -> List[str]:
        """Parses the LLM response data (dict) and saves files to disk. Returns list of saved filenames."""
        created_files = []
        files = data.get("files", [])

        if not isinstance(files, list):
            return []

        for f in files:
            if isinstance(f, dict) and "filename" in f and "content" in f:
                try:
                    self.file_io.write_file(f["filename"], f["content"])
                    created_files.append(f["filename"])
                except Exception as e:
                    logger.error(f"Failed to write file {f.get('filename')}: {e}")

        return created_files

    def execute_step(self, step: Step, task_input: str = None) -> Tuple[Step, List[str]]:
        logger.info(f"🤖 [Fullstack] Executing: {step.description}")
        step.status = TaskStatus.IN_PROGRESS
        modified_files = []

        # 1. Indexação rápida (Contexto)
        if self.indexer:
            try: self.indexer.index_workspace()
            except: pass

        # 2. Construção do Contexto
        rag_context = ""
        if self.memory:
            try:
                hits = self.memory.search(step.description, k=3)
                for txt, meta in hits:
                    rag_context += f"\nFile: {meta.get('source')}\n{txt}\n"
            except: pass

        # 3. Prompt System
        system_prompt = """You are an Expert Fullstack Developer.
        You must implement code or write tests based on the user request.
        You have a PERSISTENT sandbox environment. You can start background processes (servers) and check them.

        OUTPUT FORMAT (STRICT JSON):
        {
            "files": [
                {"filename": "path/to/file.ext", "content": "code content..."}
            ],
            "command": "shell command to verify"
        }

        PROTOCOLO DE VERIFICAÇÃO OBRIGATÓRIO:
        - Proibido: NUNCA use echo para dizer o que você fez (ex: não faça echo "Done").
        - Obrigatório: Após criar ou editar qualquer arquivo, você DEVE rodar um comando de leitura (cat filename ou ls -l filename) na mesma execução ou na próxima, para provar que o arquivo existe e tem o conteúdo correto.
        - Seus logs são a única prova que o Revisor tem. Sem logs de comando real = Reprovação.

        SPECIAL COMMANDS FOR 'command' FIELD:
        - "BG_START: <command>" -> Starts a background process (e.g. "BG_START: python server.py"). Returns PID.
        - "BG_LOG: <pid>"       -> Reads logs of the process with that PID.
        - "BG_STOP: <pid>"      -> Stops the process.
        - "BG_INPUT: <pid>|<text>" -> Sends text to stdin (Experimental).

        Example: To start a server, return {"command": "BG_START: python3 -m http.server 8080"}.
        The next feedback will give you the PID. Then you can verify it with curl.

        Do not include markdown formatting (```json). Just raw JSON.
        """

        # Include task_input (feedback) if present
        extra_input = f"\nADDITIONAL INPUT/FEEDBACK:\n{task_input}" if task_input else ""
        current_context = f"TASK: {step.description}{extra_input}\n\nCONTEXT:\n{rag_context}"

        attempts = 0
        max_attempts = 5 # Increased for interaction loops
        history = ""

        while attempts < max_attempts:
            attempts += 1

            # Chama LLM com modo JSON
            # Nota: O LLMProvider agora lida com o modo JSON mesmo para o LocalOpenAIClient
            response = self.llm.generate_response(
                prompt=current_context + history,
                system_message=system_prompt,
                schema=None # Usando prompt engineering explícito no system_prompt
            )
            logger.debug(f"Resposta bruta do LLM: {response}")

            try:
                # Limpeza básica caso o modelo teimoso mande markdown
                clean_json = response.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                logger.debug(f"JSON decodificado com sucesso: {data}")

                # 4. Side Effects (Escrever arquivos)
                current_files = self._parse_and_save_files(data)

                # 5. Verificação / Execução de Comando
                cmd = data.get("command")
                result_output = ""
                success = True

                if not cmd:
                    step.status = TaskStatus.COMPLETED
                    step.result = "Done (No verification command)"
                    step.logs = history
                    return step, current_files

                logger.info(f"Executing command: {cmd}")

                if cmd.startswith("BG_START:"):
                    real_cmd = cmd.split("BG_START:", 1)[1].strip()
                    res = self.executor.start_background_process(real_cmd)
                    success = res["success"]
                    if success:
                        result_output = f"BG_START Success. PID: {res['pid']}. {res.get('message', '')}"
                    else:
                        result_output = f"BG_START Failed: {res.get('error')}"

                elif cmd.startswith("BG_LOG:"):
                    pid = cmd.split("BG_LOG:", 1)[1].strip()
                    res = self.executor.read_background_logs(pid)
                    success = res["success"]
                    if success:
                        result_output = f"Logs for PID {pid}:\n{res['logs']}"
                    else:
                        result_output = f"Failed to read logs: {res.get('error')}"

                elif cmd.startswith("BG_STOP:"):
                    pid = cmd.split("BG_STOP:", 1)[1].strip()
                    res = self.executor.stop_background_process(pid)
                    success = res["success"]
                    result_output = f"Stop PID {pid}: {'Success' if success else 'Failed'}. Output: {res.get('output', res.get('error'))}"

                else:
                    # Standard sync command
                    res = self.executor.run_command(cmd)
                    success = res["success"]
                    result_output = res["output"]

                logger.info(f"Result: {result_output[:200]}...")

                if success:
                    # If it's a BG_START, we usually want to continue (loop) to verify it?
                    # Or should we consider it "Complete" if the task was just "Start the server"?
                    # The workflow is: Planner creates step "Start Server". Fullstack executes "BG_START". Success. Done.
                    # Next step: "Verify Server". Fullstack executes "curl ...". Success. Done.
                    # This seems correct.

                    step.status = TaskStatus.COMPLETED
                    step.result = f"Success! Output: {result_output[:500]}..."
                    step.logs = history + "\n" + result_output
                    return step, current_files
                else:
                    # Self-Healing
                    history += f"\n\nATTEMPT {attempts} FAILED:\nCommand: {cmd}\nOutput: {result_output}\n\nFix the code and try again."
                    logger.info(f"Self-healing attempt {attempts}...")
                    modified_files = current_files # Keep track

            except json.JSONDecodeError as e:
                logger.error(f"Erro de decodificação JSON: {e}. Resposta recebida: {clean_json}")
                history += "\n\nERROR: Invalid JSON response. Please format as valid JSON."
            except Exception as e:
                logger.error(f"Erro inesperado no loop de execução: {e}")
                history += f"\n\nERROR: {str(e)}"

        step.status = TaskStatus.FAILED
        step.logs = history
        step.result = "Failed after max attempts."
        return step, modified_files
