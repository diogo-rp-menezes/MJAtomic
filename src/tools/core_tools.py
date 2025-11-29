import os
from langchain.tools import tool
# Importe a ferramenta segura que já existe no projeto
from src.tools.secure_executor import SecureExecutorTool
# --- NOVAS IMPORTAÇÕES ---
from src.core.memory.vector_store import VectorMemory
from src.core.memory.indexer import CodeIndexer
from src.core.logger import logger

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

# --- NOVAS FERRAMENTAS ---

@tool
def search_codebase(query: str) -> str:
    """
    Busca na base de conhecimento do código por trechos relevantes a uma pergunta ou termo.
    Use esta ferramenta ANTES de escrever um novo código para encontrar exemplos, reutilizar lógica
    ou entender como as coisas funcionam no projeto.
    Exemplo: search_codebase('como a autenticação de usuário é implementada?')
    """
    logger.info(f"🧠 Executando busca na base de código com a query: {query}")
    try:
        memory = VectorMemory()
        results = memory.search(query, k=3)
        if not results:
            return "Nenhum resultado relevante encontrado na base de código."

        context = "Resultados da busca na base de código:\n\n"
        for text, metadata in results:
            context += f"--- Trecho do arquivo: {metadata.get('source', 'desconhecido')} ---\n"
            context += f"{text}\n\n"
        return context
    except Exception as e:
        return f"Erro ao executar a busca na base de código: {str(e)}"

@tool
def update_codebase_memory() -> str:
    """
    Força a re-indexação de todo o workspace para atualizar a memória de longo prazo.
    Use esta ferramenta DEPOIS de criar novos arquivos ou fazer modificações significativas,
    para garantir que a memória do código esteja atualizada para as próximas tarefas.
    """
    logger.info("🧠 Atualizando a memória da base de código...")
    try:
        indexer = CodeIndexer(workspace_path=WORKSPACE_PATH)
        indexer.index_workspace()
        return "Memória da base de código atualizada com sucesso."
    except Exception as e:
        return f"Erro ao atualizar a memória da base de código: {str(e)}"

# Lista de todas as ferramentas para fácil importação
core_tools = [
    write_file,
    read_file,
    list_files,
    execute_command,
    search_codebase,
    update_codebase_memory
]
