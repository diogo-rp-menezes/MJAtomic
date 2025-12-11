from src.core.interfaces import ILLMProvider
from src.tools.file_io import FileIOTool
from src.tools.architect.document_generator import DocumentGeneratorTool
from src.tools.architect.project_builder import StructureBuilderTool
from src.tools.secure_executor import SecureExecutorTool
from src.tools.git_tool import GitTool

class ArchitectAgent:
    def __init__(self, llm: ILLMProvider, workspace_path: str = "./workspace"):
        self.llm = llm
        self.file_io = FileIOTool(root_path=workspace_path)
        self.doc_gen = DocumentGeneratorTool(self.llm)
        self.builder = StructureBuilderTool(self.llm, self.file_io)
        self.executor = SecureExecutorTool(workspace_path=workspace_path)
        self.git_tool = GitTool(self.executor)

    def init_project(self, project_name: str, description: str, stack_preference: str = "") -> str:
        final_stack = stack_preference
        if not final_stack or len(final_stack) < 3:
            final_stack = "Recomendada pelo Arquiteto (Análise de Trade-offs baseada na descrição)"

        # 1. Guidelines
        guidelines = self.doc_gen.generate_guideline(project_name, description, final_stack)
        self.file_io.write_file(".ai/guidelines.md", guidelines)

        # 2. README
        readme = self.doc_gen.generate_readme(project_name, guidelines)
        self.file_io.write_file("README.md", readme)

        # 3. Gitignore (Upgraded Signature)
        gitignore = self.doc_gen.generate_gitignore(project_name, guidelines)
        self.file_io.write_file(".gitignore", gitignore)

        # 4. Contributing
        contributing = self.doc_gen.generate_contributing_md(project_name, guidelines)
        self.file_io.write_file("CONTRIBUTING.md", contributing)

        # 5. License (Default MIT)
        license_text = self.doc_gen.generate_license(license_type="MIT", holder="DevAgent User")
        self.file_io.write_file("LICENSE", license_text)

        # 6. Changelog
        changelog = self.doc_gen.generate_changelog(project_name)
        self.file_io.write_file("CHANGELOG.md", changelog)

        # 7. Structure
        structure = self.builder.generate_structure(guidelines)
        self.builder.build_project(structure, guidelines, project_name)

        # 8. Git Init
        try:
            git_init_msg = self.git_tool.init_repo()
            git_commit_msg = self.git_tool.initial_commit()
            git_status = f"{git_init_msg}\n{git_commit_msg}"
        except Exception as e:
            git_status = f"Git initialization failed: {e}"

        return f"Projeto '{project_name}' inicializado! Stack definida: {final_stack}. Arquivos: {len(structure.get('files', []))}.\n\nGit Status:\n{git_status}"
