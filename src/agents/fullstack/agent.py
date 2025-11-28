from src.core.models import Step, TaskStatus
from src.core.llm.provider import LLMProvider
from src.core.memory.vector_store import VectorMemory
from src.core.memory.indexer import CodeIndexer
from src.tools.file_io import FileIOTool
from src.tools.secure_executor import SecureExecutorTool
from src.core.logger import logger
import os
import yaml
import json

class FullstackAgent:
    def __init__(self,
                 workspace_path: str = "./workspace",
                 llm_provider: LLMProvider = None,
                 file_io: FileIOTool = None,
                 executor: SecureExecutorTool = None,
                 memory = None,
                 indexer = None):

        self.workspace_path = workspace_path

        # Injeção de Dependência ou Default
        self.llm = llm_provider or LLMProvider(profile="fast")
        self.file_io = file_io or FileIOTool(root_path=self.workspace_path)
        self.executor = executor or SecureExecutorTool(workspace_path=self.workspace_path)
        self.memory = memory
        self.indexer = indexer

        # Carrega config se existir
        self.config = self._load_config(os.path.join(workspace_path, "config.yaml"))

        # Lazy Load de memória se não injetado e não falhar
        if self.memory is None:
            try:
                self.memory = VectorMemory()
                self.indexer = CodeIndexer(workspace_path=self.workspace_path)
            except:
                logger.warning("Running FullstackAgent without Vector Memory (Degraded Mode)")

    def _load_config(self, path: str) -> dict:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f: return yaml.safe_load(f)
            except: pass
        return {}

    def _parse_and_save_files(self, response_data: dict) -> list:
        """Helper to parse 'files' from JSON response and save them."""
        created_files = []
        if "files" in response_data and isinstance(response_data["files"], list):
            for f in response_data["files"]:
                if "filename" in f and "content" in f:
                    try:
                        self.file_io.write_file(f["filename"], f["content"])
                        created_files.append(f["filename"])
                    except Exception as e:
                        logger.error(f"Failed to write file {f['filename']}: {e}")
        return created_files

    def execute_step(self, step: Step) -> Step:
        logger.info(f"🤖 [Fullstack] Executing: {step.description}")
        step.status = TaskStatus.IN_PROGRESS

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

        OUTPUT FORMAT (STRICT JSON):
        {
            "files": [
                {"filename": "path/to/file.ext", "content": "code content..."}
            ],
            "command": "shell command to verify (e.g. pytest)"
        }

        Do not include markdown formatting (```json). Just raw JSON.
        """

        current_context = f"TASK: {step.description}\n\nCONTEXT:\n{rag_context}"

        attempts = 0
        max_attempts = 3
        history = ""

        while attempts < max_attempts:
            attempts += 1

            # Chama LLM com modo JSON
            response = self.llm.generate_response(
                prompt=current_context + history,
                system_message=system_prompt,
                json_mode=True
            )

            try:
                # Limpeza básica caso o modelo teimoso mande markdown
                clean_json = response.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)

                # 4. Side Effects (Escrever arquivos)
                # Use helper method for consistency and testability
                self._parse_and_save_files(data)

                # 5. Verificação
                cmd = data.get("command")
                if not cmd:
                    step.status = TaskStatus.COMPLETED
                    step.result = "Done (No verification command)"
                    return step

                result = self.executor.run_command(cmd)

                if result["exit_code"] == 0:
                    step.status = TaskStatus.COMPLETED
                    step.result = f"Success! Output: {result['output'][:100]}..."
                    step.logs = result["output"]
                    return step
                else:
                    # Self-Healing: Adiciona erro ao contexto e tenta de novo
                    history += f"\n\nATTEMPT {attempts} FAILED:\nCommand: {cmd}\nOutput: {result['output']}\n\nFix the code and try again."
                    logger.info(f"Self-healing attempt {attempts}...")

            except json.JSONDecodeError:
                history += "\n\nERROR: Invalid JSON response. Please format as valid JSON."
            except Exception as e:
                history += f"\n\nERROR: {str(e)}"

        step.status = TaskStatus.FAILED
        step.logs = history
        step.result = "Failed after max attempts."
        return step
