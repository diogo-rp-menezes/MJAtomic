import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_postgres import PGVectorStore, PGEngine
from src.core.llm.embedding_provider import EmbeddingProvider
from src.core.logger import logger

class CodeIndexer:
    def __init__(self, workspace_path: str):
        if not os.path.isdir(workspace_path):
            raise ValueError(f"O caminho do workspace '{workspace_path}' não é um diretório válido.")
        self.workspace_path = workspace_path
        self.embedding_provider = EmbeddingProvider()

        self.connection_string = os.getenv("POSTGRES_URL")
        if not self.connection_string:
            raise ValueError("A variável de ambiente POSTGRES_URL não está definida.")

        # Normaliza para driver psycopg3 quando necessário
        if "postgresql+psycopg2://" in self.connection_string:
            self.connection_string = self.connection_string.replace("postgresql+psycopg2://", "postgresql+psycopg://")
        elif self.connection_string.startswith("postgresql://"):
            self.connection_string = self.connection_string.replace("postgresql://", "postgresql+psycopg://")

        self.collection_name = os.getenv("PGVECTOR_COLLECTION_NAME", "code_collection")

    def index_workspace(self):
        """
        Carrega, divide e indexa todos os arquivos de código do workspace no banco de dados vetorial.
        Usa os.walk manual para filtragem rigorosa de diretórios proibidos.
        """
        logger.info(f"Iniciando indexação do workspace: {self.workspace_path}")

        documents = []

        # Lista de diretórios a serem ignorados
        exclude_dirs = {
            '.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env',
            'dist', 'build', '.idea', '.vscode', 'site-packages'
        }

        # Extensões válidas
        valid_extensions = {
            '.py', '.js', '.ts', '.html', '.css', '.md', '.txt',
            '.json', '.yml', '.yaml', '.sh', '.Dockerfile'
        }

        has_files = False

        for root, dirs, files in os.walk(self.workspace_path):
            # Filtragem in-place para impedir que os.walk entre em diretórios proibidos
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                # Verifica extensão ou nome exato (Dockerfile)
                _, ext = os.path.splitext(file)
                if ext in valid_extensions or file == 'Dockerfile':
                    has_files = True
                    file_path = os.path.join(root, file)
                    try:
                        loader = TextLoader(file_path, autodetect_encoding=True)
                        docs = loader.load()
                        documents.extend(docs)
                    except Exception as e:
                        logger.warning(f"Erro ao carregar arquivo {file_path}: {e}")

        if not has_files:
            logger.info("Workspace vazio ou sem arquivos de código relevantes. Pulando indexação.")
            return

        if not documents:
            logger.warning("Nenhum documento válido encontrado para indexar após filtragem.")
            return

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        splits = text_splitter.split_documents(documents)

        if not splits:
            logger.warning("Nenhum chunk gerado após split.")
            return

        embeddings = self.embedding_provider.get_embeddings()

        logger.info(f"Indexando {len(splits)} chunks de documentos na coleção '{self.collection_name}'...")

        # Cria ou atualiza o banco de dados vetorial com os novos documentos
        try:
            # A API instalada (langchain-postgres 0.0.16) espera um PGEngine e usa 'table_name'
            engine = PGEngine.from_connection_string(self.connection_string)

            store = PGVectorStore.create_sync(
                engine=engine,
                embedding_service=embeddings,
                table_name=self.collection_name,
                id_column="langchain_id",
                metadata_json_column="cmetadata",
            )

            # Observação: algumas versões não expõem 'drop'/'clear'.
            # Mantemos apenas a adição; se necessário, a limpeza pode ser feita externamente.
            store.add_documents(splits)
        except Exception as e:
            logger.error(f"Falha ao indexar documentos no PGVectorStore: {e}")
            raise

        logger.info("Indexação do workspace concluída com sucesso.")
