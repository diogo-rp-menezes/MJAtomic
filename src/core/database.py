import os
from sqlalchemy import create_engine
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

    # 1. Cria tabelas da aplicação (DevelopmentPlan, Steps)
    Base.metadata.create_all(bind=engine)

    # 2. Cria tabelas do LangGraph (checkpoints, writes, etc.)
    conn_str = get_db_connection_string()
    with PostgresSaver.from_conn_string(conn_str) as saver:
        saver.setup()
