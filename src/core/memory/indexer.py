import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, DirectoryLoader
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
        """
        # [NOVO] Verificação rápida de pré-condição
        has_files = False
        extensions = {
            '.py', '.js', '.ts', '.md', '.rs', '.toml', '.yaml', '.yml', '.json', '.html', '.css',
            '.sh', '.env.example', 'Dockerfile'
        }

        for root, _, files in os.walk(self.workspace_path):
            if any(f.endswith(tuple(extensions)) for f in files):
                has_files = True
                break

        if not has_files:
            logger.info("Workspace vazio ou sem arquivos de código relevantes. Pulando indexação.")
            return

        logger.info(f"Iniciando indexação do workspace: {self.workspace_path}")

        # Carregador para múltiplos tipos de arquivo de código
        loader = DirectoryLoader(
            self.workspace_path,
            glob="**/*[.py,.js,.ts,.md,.rs,.toml,.yaml,.json]",
            loader_cls=TextLoader,
            show_progress=True,
            use_multithreading=True,
            silent_errors=True
        )

        documents = loader.load()
        if not documents:
            logger.warning("Nenhum documento encontrado para indexar.")
            return

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
        splits = text_splitter.split_documents(documents)

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
            )

            # Observação: algumas versões não expõem 'drop'/'clear'.
            # Mantemos apenas a adição; se necessário, a limpeza pode ser feita externamente.
            store.add_documents(splits)
        except Exception as e:
            logger.error(f"Falha ao indexar documentos no PGVectorStore: {e}")
            raise

        logger.info("Indexação do workspace concluída com sucesso.")
