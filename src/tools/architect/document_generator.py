from src.core.llm.provider import LLMProvider
import re
from datetime import datetime

class DocumentGeneratorTool:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def _clean_response(self, text) -> str:
        if isinstance(text, list):
            text = " ".join([str(t) for t in text])
        if not isinstance(text, str):
            text = str(text)

        # Basic cleaning of markdown blocks if present (though prompts often ask for pure text)
        text = re.sub(r'^```[a-zA-Z0-9]*\n', '', text.strip())
        text = re.sub(r'\n```$', '', text.strip())
        return text

    def generate_guideline(self, project_name: str, description: str, stack: str) -> str:
        prompt = f"""
        Você é um arquiteto de software criando o `guidelines.md` para o projeto "{project_name}".
        Descrição: {description}
        Stack Escolhida: {stack}
        Gere um `guidelines.md` completo, profundo e bem estruturado com seções para Visão, Arquitetura, Stack, Estrutura de Projeto, Qualidade, Convenções, Roadmap e a regra dos "Documentos Vivos".
        """
        res = self.llm.generate_response(prompt)
        return self._clean_response(res)

    def generate_readme(self, project_name: str, guideline_content: str) -> str:
        prompt = f"""
        Aja como um engenheiro de software sênior. Usando o `guidelines.md` abaixo como única fonte da verdade, crie um `README.md` profissional para o projeto "{project_name}".
        O README deve ser claro, conciso e bem formatado.

        Contexto (guidelines.md):
        ---
        {guideline_content}
        ---
        """
        res = self.llm.generate_response(prompt)
        return self._clean_response(res)

    def generate_contributing_md(self, project_name: str, guideline_content: str) -> str:
        prompt = f"""
        Aja como um mantenedor de um projeto open-source. Crie um guia de contribuição (`CONTRIBUTING.md`) detalhado para o projeto "{project_name}", usando o `guidelines.md` fornecido como única fonte da verdade.

        Contexto (guidelines.md):
        ---
        {guideline_content}
        ---
        """
        res = self.llm.generate_response(prompt)
        return self._clean_response(res)

    def generate_license(self, license_type: str, year: str = None, holder: str = "DevAgent User") -> str:
        if not year:
            year = str(datetime.now().year)

        prompt = f"""
        Gere o texto completo e exato da licença open source '{license_type}'.
        O ano a ser usado no copyright é {year}.
        O titular do copyright é "{holder}".
        Retorne apenas o texto puro da licença, sem nenhuma explicação ou formatação extra.
        """
        res = self.llm.generate_response(prompt)
        return self._clean_response(res)

    def generate_gitignore(self, project_name: str, guideline_content: str) -> str:
        prompt = f"""
        Aja como um especialista em Git. Crie um arquivo `.gitignore` abrangente e bem comentado para o projeto "{project_name}", com base na stack descrita no `guidelines.md` abaixo.

        Contexto (guidelines.md):
        ---
        {guideline_content}
        ---
        """
        res = self.llm.generate_response(prompt)
        text = self._clean_response(res)
        return text.replace("`gitignore", "").replace("`", "").strip()

    def generate_changelog(self, project_name: str) -> str:
        prompt = f"""
        Aja como um engenheiro de software que segue as melhores práticas de versionamento.
        Crie um arquivo `CHANGELOG.md` inicial para o projeto "{project_name}" seguindo estritamente o formato do "Keep a Changelog".
        Inclua uma seção `[Unreleased]` no topo e um exemplo para a versão `[0.1.0]`.
        """
        res = self.llm.generate_response(prompt)
        return self._clean_response(res)
