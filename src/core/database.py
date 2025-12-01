import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

user = os.getenv("POSTGRES_USER", "devagent")
password = os.getenv("POSTGRES_PASSWORD", "atomicpass")
host = os.getenv("POSTGRES_HOST", "db")
port = os.getenv("POSTGRES_PORT", "5432")
db_name = os.getenv("POSTGRES_DB", "devagent_db")

DATABASE_URL = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from src.core.orm_models import DBDevelopmentPlan, DBStep
    from langgraph.checkpoint.postgres import PostgresSaver
    from src.core.graph.checkpoint import get_db_connection_string

    Base.metadata.create_all(bind=engine)

    # Verificação e migração da tabela checkpoints
    try:
        insp = inspect(engine)
        if "checkpoints" in insp.get_table_names():
            columns = [c["name"] for c in insp.get_columns("checkpoints")]
            # Se a tabela existe mas não tem a coluna esperada pelo LangGraph v3+
            if "checkpoint_ns" not in columns:
                print("MIGRAÇÃO: Tabela 'checkpoints' legado detectada. Dropando para recriação correta...")
                with engine.connect() as conn:
                    conn.execute(text("DROP TABLE checkpoints CASCADE"))
                    conn.commit()
    except Exception as e:
        print(f"AVISO: Erro ao verificar migração de checkpoints: {e}")

    # Cria tabelas do LangGraph Checkpointer
    try:
        conn_str = get_db_connection_string()
        with PostgresSaver.from_conn_string(conn_str) as saver:
            saver.setup()
    except Exception as e:
        # Loga mas não quebra se for apenas configuração de teste (ex: sem POSTGRES_URL)
        print(f"AVISO: Falha ao inicializar tabelas do LangGraph (pode ser ignorado em testes sem Postgres): {e}")
