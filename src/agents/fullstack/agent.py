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

        OUTPUT FORMAT (STRICT JSON):
        {
            "files": [
                {"filename": "path/to/file.ext", "content": "code content..."}
            ],
            "command": "shell command to verify (e.g. pytest)"
        }

        Do not include markdown formatting (```json). Just raw JSON.
        """

        # Include task_input (feedback) if present
        extra_input = f"\nADDITIONAL INPUT/FEEDBACK:\n{task_input}" if task_input else ""
        current_context = f"TASK: {step.description}{extra_input}\n\nCONTEXT:\n{rag_context}"

        attempts = 0
        max_attempts = 3
        history = ""

        while attempts < max_attempts:
            attempts += 1

            # Chama LLM com modo JSON
            response = self.llm.generate_response(
                prompt=current_context + history,
                system_message=system_prompt
            )

            try:
                # Limpeza básica caso o modelo teimoso mande markdown
                clean_json = response.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)

                # 4. Side Effects (Escrever arquivos)
                current_files = self._parse_and_save_files(data)

                # 5. Verificação
                cmd = data.get("command")
                if not cmd:
                    step.status = TaskStatus.COMPLETED
                    step.result = "Done (No verification command)"
                    step.logs = history
                    return step, current_files

                result = self.executor.run_command(cmd)

                if result["exit_code"] == 0:
                    step.status = TaskStatus.COMPLETED
                    step.result = f"Success! Output: {result['output'][:100]}..."
                    step.logs = history + "\n" + result["output"]
                    return step, current_files
                else:
                    # Self-Healing: Adiciona erro ao contexto e tenta de novo
                    history += f"\n\nATTEMPT {attempts} FAILED:\nCommand: {cmd}\nOutput: {result['output']}\n\nFix the code and try again."
                    logger.info(f"Self-healing attempt {attempts}...")
                    modified_files = current_files # Keep track, though we might overwrite next attempt

            except json.JSONDecodeError:
                history += "\n\nERROR: Invalid JSON response. Please format as valid JSON."
            except Exception as e:
                history += f"\n\nERROR: {str(e)}"

        step.status = TaskStatus.FAILED
        step.logs = history
        step.result = "Failed after max attempts."
        return step, modified_files
