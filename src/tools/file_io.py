import os
import re
from typing import List, Optional

class FileIOTool:
    def __init__(self, root_path: str = "./workspace"):
        self.root_path = root_path
        os.makedirs(self.root_path, exist_ok=True)

    def _get_full_path(self, filepath: str) -> str:
        # Dynamic normalization: remove root directory name if it appears at start
        # e.g. "workspace/app/main.py" -> "app/main.py" if root is "./workspace"
        root_name = os.path.basename(os.path.abspath(self.root_path))
        parts = filepath.split(os.sep)
        if parts and parts[0] == root_name:
            filepath = os.sep.join(parts[1:])

        full_path = os.path.abspath(os.path.join(self.root_path, filepath))
        if not full_path.startswith(os.path.abspath(self.root_path)):
            raise ValueError("Access to files outside workspace is prohibited.")
        return full_path

    def _sanitize_content(self, content: str) -> str:
        """Remove markdown code blocks wrappers de forma agressiva."""
        # Remove linha inicial tipo ```rust ou ```
        content = re.sub(r'^```[a-zA-Z0-9]*\n', '', content.strip())
        # Remove linha final ```
        content = re.sub(r'\n```$', '', content.strip())
        # Remove linhas que sobraram que sÃ³ tenham ```
        content = re.sub(r'\n```\n', '\n', content)
        return content

    def write_file(self, filepath: str, content: str) -> str:
        # Security: Block write to binary extensions
        forbidden_exts = (
            '.db', '.sqlite', '.sqlite3', '.png', '.jpg', '.pyc',
            '.pdf', '.zip', '.tar', '.gz', '.ico', '.woff', '.ttf',
            '.eot', '.bin', '.exe', '.dll', '.so'
        )
        if filepath.lower().endswith(forbidden_exts):
            raise ValueError(f"Security/Integrity Error: Cannot write text content to binary file extension {os.path.splitext(filepath)[1]}. Use database connection or binary handling.")

        clean_content = self._sanitize_content(content)
        path = self._get_full_path(filepath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(clean_content)
        return f"Arquivo {filepath} escrito com sucesso."

    def read_file(self, filepath: str) -> str:
        path = self._get_full_path(filepath)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo {filepath} nÃ£o encontrado.")
        with open(path, "r", encoding="utf-8") as f:
            # Ao ler, tambÃ©m aplicamos uma limpeza leve para nÃ£o alimentar o LLM com lixo antigo
            content = f.read()
            if content.strip().startswith("```") or content.strip().endswith("```"):
                 return self._sanitize_content(content)
            return content

    def get_project_structure(self) -> str:
        """Retorna a Ã¡rvore de arquivos e o conteÃºdo de arquivos relevantes."""
        output = []
        ignore_dirs = {'.git', '__pycache__', 'node_modules', 'target', 'venv', '.idea', '.vscode', '.ai'}
        priority_files = {'Cargo.toml', 'pyproject.toml', 'package.json', 'README.md', 'guidelines.md', 'main.rs', 'main.py', 'App.java', 'app.rs', 'lib.rs', 'mod.rs'}

        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            level = root.replace(self.root_path, '').count(os.sep)
            indent = ' ' * 4 * (level)
            output.append(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 4 * (level + 1)

            for file in files:
                if file.endswith(('.pyc', '.lock', '.png', '.jpg', '.exe', '.log')): continue

                output.append(f"{subindent}{file}")

                if file in priority_files or file.endswith(('.rs', '.py')):
                    try:
                        path = os.path.join(root, file)
                        size = os.path.getsize(path)
                        if size < 15000:
                            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                # Limpeza on-the-fly para leitura tambÃ©m
                                clean_read = re.sub(r'^```[a-z]*\n|\n```$', '', content.strip())
                                output.append(f"{subindent}  --- CONTENT ({file}) ---")
                                output.append(f"{subindent}  {clean_read[:3000]}...")
                                output.append(f"{subindent}  --- END CONTENT ---")
                    except: pass

        return "\n".join(output)
