from pydantic_settings import BaseSettings
from typing import Optional, Literal

class Settings(BaseSettings):
    # Database
    POSTGRES_URL: str = "postgresql+psycopg://devagent:atomicpass@localhost:5432/devagent_db"
    POSTGRES_USER: str = "devagent"
    POSTGRES_PASSWORD: str = "atomicpass"
    POSTGRES_DB: str = "devagent_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"

    # Vector DB
    PGVECTOR_COLLECTION_NAME: str = "code_collection"

    # LLM Global Configuration
    LLM_PROVIDER: Literal["google", "ollama", "local"] = "google"

    # Specific Agents Configuration
    FULLSTACK_MODEL: str = "gemini-2.5-flash"
    FULLSTACK_BASE_URL: Optional[str] = None

    TECH_LEAD_MODEL: str = "gemini-2.5-flash"

    # Embeddings
    EMBEDDING_PROVIDER: Literal["google", "ollama", "local"] = "google"
    GOOGLE_EMBEDDING_MODEL: str = "embedding-001"

    # Ollama / Local specific
    OLLAMA_BASE_URL: Optional[str] = None
    OLLAMA_EMBEDDING_MODEL: str = "qwen3-embedding:0.6b"

    # Workspace
    LOCAL_WORKSPACE_PATH: str = "./workspace"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
