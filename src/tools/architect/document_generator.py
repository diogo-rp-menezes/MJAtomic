from src.core.llm.provider import LLMProvider
import re

class DocumentGeneratorTool:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def _clean_response(self, text) -> str:
        if isinstance(text, list):
            text = " ".join([str(t) for t in text])
        if not isinstance(text, str):
            return str(text)
        return text

    def generate_guideline(self, project_name: str, description: str, stack: str) -> str:
        prompt = f"""
        VocÃª Ã© um Arquiteto de Software SÃªnior.
        Crie o arquivo guidelines.md para o projeto "{project_name}".
        DESCRIÃ‡ÃƒO: {description}
        STACK: {stack}
        Retorne APENAS o conteÃºdo Markdown.
        """
        res = self.llm.generate_response(prompt)
        return self._clean_response(res)

    def generate_readme(self, project_name: str, guideline_content: str) -> str:
        prompt = f"""
        Crie um README.md para "{project_name}" baseado nestas diretrizes:
        {guideline_content[:4000]}...
        """
        res = self.llm.generate_response(prompt)
        return self._clean_response(res)

    def generate_gitignore(self, stack: str) -> str:
        prompt = f"Gere um .gitignore para: {stack}. Apenas o cÃ³digo."
        res = self.llm.generate_response(prompt)
        text = self._clean_response(res)
        return text.replace("`gitignore", "").replace("`", "").strip()
