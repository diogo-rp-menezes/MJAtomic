import os
from langchain.tools import tool
# Importe a ferramenta segura que já existe no projeto
from src.tools.secure_executor import SecureExecutorTool

# O caminho do workspace será lido de uma variável de ambiente para flexibilidade
WORKSPACE_PATH = os.getenv("MJATOMIC_WORKSPACE_PATH", "./workspace")

def _resolve_path(filename: str) -> str:
    """Resolve o caminho do arquivo para garantir que ele esteja dentro do workspace."""
    # Garante que o diretório base exista
    os.makedirs(WORKSPACE_PATH, exist_ok=True)

    # Previne ataques de "directory traversal" (ex: ../../etc/passwd)
    absolute_workspace = os.path.abspath(WORKSPACE_PATH)
    absolute_filepath = os.path.abspath(os.path.join(absolute_workspace, filename))

    if not absolute_filepath.startswith(absolute_workspace):
        raise ValueError("Erro de Segurança: Acesso a arquivos fora do workspace é proibido.")

    return absolute_filepath

@tool
def write_file(filename: str, content: str) -> str:
    """
    Escreve ou sobrescreve o conteúdo de um arquivo no diretório de trabalho.
    Use esta ferramenta para criar novos arquivos de código, testes ou modificar arquivos existentes.
    Exemplo: write_file('src/main.py', 'print("Hello, World!")')
    """
    try:
        filepath = _resolve_path(filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Arquivo '{filename}' escrito com sucesso."
    except Exception as e:
        return f"Erro ao escrever o arquivo '{filename}': {str(e)}"

@tool
def read_file(filename: str) -> str:
    """
    Lê e retorna o conteúdo completo de um arquivo no diretório de trabalho.
    Use esta ferramenta para examinar o código existente antes de fazer modificações.
    Exemplo: read_file('src/main.py')
    """
    try:
        filepath = _resolve_path(filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Erro: Arquivo '{filename}' não encontrado."
    except Exception as e:
        return f"Erro ao ler o arquivo '{filename}': {str(e)}"

@tool
def list_files(path: str = ".") -> str:
    """
    Lista todos os arquivos e diretórios em um caminho específico dentro do diretório de trabalho.
    Use '.' para listar o conteúdo da raiz do workspace.
    Exemplo: list_files('src')
    """
    try:
        base_path = _resolve_path(path)
        entries = os.listdir(base_path)
        if not entries:
            return f"O diretório '{path}' está vazio."
        return "\n".join(entries)
    except FileNotFoundError:
        return f"Erro: Diretório '{path}' não encontrado."
    except Exception as e:
        return f"Erro ao listar arquivos em '{path}': {str(e)}"

@tool
def execute_command(command: str) -> str:
    """
    Executa um comando shell de forma segura em um ambiente isolado (Docker) e retorna sua saída.
    Use esta ferramenta para rodar testes, instalar dependências ou verificar a versão de ferramentas.
    Exemplo: execute_command('pytest tests/')
    """
    try:
        # Usa o executor seguro já existente no projeto.
        executor = SecureExecutorTool(workspace_path=WORKSPACE_PATH)
        result = executor.run_command(command)

        output = f"Comando executado. Código de Saída: {result['exit_code']}\n"
        output += f"Saída (stdout/stderr):\n{result['output']}"
        return output
    except Exception as e:
        return f"Erro ao instanciar ou executar o comando seguro: {str(e)}"

# Lista de todas as ferramentas para fácil importação
core_tools = [write_file, read_file, list_files, execute_command]
