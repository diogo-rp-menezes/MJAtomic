import logging
from pathlib import Path

class BaseAgent:
    """
    A classe base para todos os agentes, fornecendo funcionalidades comuns.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def _load_prompt_template(self, file_path: str) -> str:
        """
        Carrega o conteúdo de um arquivo de template de prompt.
        """
        try:
            return Path(file_path).read_text(encoding="utf-8")
        except FileNotFoundError:
            self.logger.error(f"Arquivo de prompt não encontrado: {file_path}")
            raise
