from src.core.llm.provider import LLMProvider
from src.tools.file_io import FileIOTool
from src.tools.architect.document_generator import DocumentGeneratorTool
from src.tools.architect.project_builder import StructureBuilderTool
import os

class ArchitectAgent:
    def __init__(self, workspace_path: str = "./workspace"):
        model_name = os.getenv("ARCHITECT_MODEL", "gemini-1.5-flash")
        self.llm = LLMProvider(model_name=model_name)
        self.file_io = FileIOTool(root_path=workspace_path)
        self.doc_gen = DocumentGeneratorTool(self.llm)
        self.builder = StructureBuilderTool(self.llm, self.file_io)

    def init_project(self, project_name: str, description: str, stack_preference: str = "") -> str:
        final_stack = stack_preference
        if not final_stack or len(final_stack) < 3:
            final_stack = "Recomendada pelo Arquiteto (Análise de Trade-offs baseada na descrição)"

        guidelines = self.doc_gen.generate_guideline(project_name, description, final_stack)
        self.file_io.write_file(".ai/guidelines.md", guidelines)

        readme = self.doc_gen.generate_readme(project_name, guidelines)
        self.file_io.write_file("README.md", readme)

        gitignore = self.doc_gen.generate_gitignore(final_stack)
        self.file_io.write_file(".gitignore", gitignore)

        structure = self.builder.generate_structure(guidelines)

        self.builder.build_project(structure, guidelines, project_name)

        return f"Projeto '{project_name}' inicializado! Stack definida: {final_stack}. Arquivos: {len(structure.get('files', []))}."
