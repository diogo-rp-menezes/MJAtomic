import json
import re
import os
from src.core.llm.provider import LLMProvider
from src.tools.file_io import FileIOTool
from src.core.logger import logger

class StructureBuilderTool:
    def __init__(self, llm_provider: LLMProvider, file_io: FileIOTool):
        self.llm = llm_provider
        self.file_io = file_io

    def _clean_response(self, text) -> str:
        if isinstance(text, list):
            text = " ".join([str(t) for t in text])
        return str(text)

    def generate_structure(self, guideline_content: str) -> dict:
        prompt = f"""
        Defina a estrutura de pastas e arquivos baseada no guideline.
        Diretrizes: {guideline_content[:4000]}

        JSON Obrigatório:
        {{ "directories": ["src"], "files": ["src/main.py"] }}
        """
        response = self.llm.generate_response(prompt)
        text = self._clean_response(response)

        try:
            cleaned = re.sub(r'`json|`', '', text).strip()
            # Tenta achar o JSON
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match: cleaned = match.group(0)
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Erro parse estrutura: {e}")
            return {"directories": [], "files": []}

    def generate_file_content(self, filepath: str, guideline_content: str, project_name: str) -> str:
        prompt = f"""
        Gere o código inicial para {filepath} do projeto "{project_name}".
        Contexto: {guideline_content[:2000]}
        Retorne APENAS o código puro.
        """
        response = self.llm.generate_response(prompt)
        text = self._clean_response(response)
        # Remove markdown
        return re.sub(r'^`\w*\n|`$', '', text.strip(), flags=re.MULTILINE)

    def build_project(self, structure: dict, guideline_content: str, project_name: str):
        for directory in structure.get("directories", []):
            full_path = os.path.join(self.file_io.root_path, directory)
            os.makedirs(full_path, exist_ok=True)

        forbidden_exts = (
            '.db', '.sqlite', '.sqlite3', '.png', '.jpg', '.pyc',
            '.pdf', '.zip', '.tar', '.gz', '.ico', '.woff', '.ttf',
            '.eot', '.bin', '.exe', '.dll', '.so'
        )

        for filepath in structure.get("files", []):
            if filepath.lower().endswith(forbidden_exts):
                logger.warning(f"Skipping binary file creation for {filepath} during architecture scaffold.")
                continue

            try:
                content = self.generate_file_content(filepath, guideline_content, project_name)
                self.file_io.write_file(filepath, content)
            except ValueError as ve:
                logger.error(f"Security/Integrity Error skipping {filepath}: {ve}")
                continue
            except Exception as e:
                logger.error(f"Failed to create file {filepath}: {e}")
                continue
