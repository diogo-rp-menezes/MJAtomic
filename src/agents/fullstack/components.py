import json
from typing import Tuple, List, Optional
from src.core.interfaces import IFileSystem, IExecutor
from src.core.models import Step
from src.core.logger import logger

class CommandParser:
    """Responsável por analisar strings de comando e identificar o tipo de ação."""

    @staticmethod
    def parse(command: str) -> Tuple[str, str]:
        """
        Analisa o comando e retorna (tipo, conteúdo).
        Tipos: 'BG_START', 'BG_LOG', 'BG_STOP', 'BG_INPUT', 'SHELL'.
        """
        if not command:
            return "NONE", ""

        if command.startswith("BG_START:"):
            return "BG_START", command.split("BG_START:", 1)[1].strip()
        elif command.startswith("BG_LOG:"):
            return "BG_LOG", command.split("BG_LOG:", 1)[1].strip()
        elif command.startswith("BG_STOP:"):
            return "BG_STOP", command.split("BG_STOP:", 1)[1].strip()
        elif command.startswith("BG_INPUT:"):
            return "BG_INPUT", command.split("BG_INPUT:", 1)[1].strip()
        elif command.startswith("CREATE_DIRECTORY:"):
            return "CREATE_DIRECTORY", command.split("CREATE_DIRECTORY:", 1)[1].strip()
        else:
            return "SHELL", command

class PromptBuilder:
    """Responsável por construir o contexto e prompt para o LLM."""

    SYSTEM_PROMPT = """You are an Expert Fullstack Developer.
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
    - "CREATE_DIRECTORY: <path>" -> Creates a directory and its parents (e.g., "CREATE_DIRECTORY: app/controllers").

    TOOL USAGE RULES:
    - To create or modify files, use the "files" array in the JSON output.
    - To create directories, you MUST use the "CREATE_DIRECTORY: path" command in the "command" field.
    - DO NOT use the "files" array or write_file to create directories. This will fail with "Is a directory".

    Example: To start a server, return {"command": "BG_START: python3 -m http.server 8080"}.
    The next feedback will give you the PID. Then you can verify it with curl.

    Do not include markdown formatting (```json). Just raw JSON.
    """

    def __init__(self, memory=None, indexer=None):
        self.memory = memory
        self.indexer = indexer

    def build_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    def build_context(self, step: Step, history: str, task_input: str = None) -> str:
        # 1. Indexação (se disponível)
        if self.indexer:
            try:
                self.indexer.index_workspace()
            except Exception as e:
                logger.warning(f"Failed to index workspace: {e}")

        # 2. RAG Context
        rag_context = ""
        if self.memory:
            try:
                # [MODIFICADO] Reduzido k para 2 para focar no essencial
                hits = self.memory.search(step.description, k=2)
                for txt, meta in hits:
                    # [NOVO] Truncagem de segurança para arquivos grandes (ex: 3000 caracteres)
                    content_preview = txt[:3000] + "\n...[restante truncado]..." if len(txt) > 3000 else txt
                    rag_context += f"\nFile: {meta.get('source', 'unknown')}\n{content_preview}\n"
            except Exception as e:
                logger.warning(f"Failed to search memory: {e}")

        extra_input = f"\nADDITIONAL INPUT/FEEDBACK:\n{task_input}" if task_input else ""
        return f"TASK: {step.description}{extra_input}\n\nCONTEXT:\n{rag_context}\n\n{history}"

class ResponseHandler:
    """Responsável por executar as ações ditadas pela resposta do LLM (Files + Commands)."""

    def __init__(self, file_system: IFileSystem, executor: IExecutor, parser: CommandParser = None):
        self.fs = file_system
        self.executor = executor
        self.parser = parser or CommandParser()

    def handle(self, data: dict) -> Tuple[str, List[str], bool]:
        """
        Processa a resposta estruturada.
        Retorna: (output_log, created_files_list, success_bool)
        """
        # 1. File Operations
        created_files = self._process_files(data.get("files", []))

        # 2. Command Execution
        cmd_str = data.get("command")
        if not cmd_str:
            return "Done (No verification command)", created_files, True

        logger.info(f"Executing command: {cmd_str}")
        cmd_type, content = self.parser.parse(cmd_str)

        output, success = self._execute_command(cmd_type, content)
        return output, created_files, success

    def _process_files(self, files_data: list) -> List[str]:
        saved = []
        if not isinstance(files_data, list):
            return []

        for f in files_data:
            if isinstance(f, dict) and "filename" in f and "content" in f:
                try:
                    self.fs.write_file(f["filename"], f["content"])
                    saved.append(f["filename"])
                except Exception as e:
                    logger.error(f"Failed to write file {f.get('filename')}: {e}")
        return saved

    def _execute_command(self, cmd_type: str, content: str) -> Tuple[str, bool]:
        """Delegates execution based on parsed command type."""
        result_output = ""
        success = False

        try:
            if cmd_type == "BG_START":
                res = self.executor.start_background_process(content)
                success = res["success"]
                if success:
                    result_output = f"BG_START Success. PID: {res['pid']}. {res.get('message', '')}"
                else:
                    result_output = f"BG_START Failed: {res.get('error')}"

            elif cmd_type == "BG_LOG":
                res = self.executor.read_background_logs(content)
                success = res["success"]
                if success:
                    result_output = f"Logs for PID {content}:\n{res['logs']}"
                else:
                    result_output = f"Failed to read logs: {res.get('error')}"

            elif cmd_type == "BG_STOP":
                res = self.executor.stop_background_process(content)
                success = res["success"]
                result_output = f"Stop PID {content}: {'Success' if success else 'Failed'}. Output: {res.get('output', res.get('error'))}"

            elif cmd_type == "BG_INPUT":
                # Assuming format pid|text
                if "|" in content:
                    pid, text = content.split("|", 1)
                    # Note: IExecutor interface might not have send_background_input defined yet?
                    # The secure_executor.py HAS it. Protocol checks might fail if not updated.
                    # I'll check IExecutor in interfaces.py later.
                    # For now, I'll assume it might be missing and skip or try.
                    # Actually SecureExecutorTool has it. IExecutor in step 1 was defined based on usage.
                    # Let's check interfaces.py content from memory/previous step.
                    # IExecutor has: run_command, start_background_process, read_background_logs, stop_background_process.
                    # It missed send_background_input!
                    # I will assume standard shell command for now or ignore BG_INPUT to be safe.
                    result_output = "BG_INPUT not supported in current interface."
                    success = False
                else:
                    result_output = "Invalid BG_INPUT format."
                    success = False

            elif cmd_type == "CREATE_DIRECTORY":
                res = self.executor.create_directory(content)
                success = res["success"]
                result_output = res.get("output", res.get("error"))

            else: # SHELL
                res = self.executor.run_command(content)
                success = res["success"]
                result_output = res["output"]

        except Exception as e:
            result_output = f"Execution Error: {str(e)}"
            success = False

        logger.info(f"Result: {result_output[:200]}...")
        return result_output, success
