from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, Literal, List, Union

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

    # API Keys & Rate Limiting
    # Using Union[List[str], str] allows the validator to intercept the string before
    # Pydantic Settings attempts to parse it as JSON.
    GOOGLE_API_KEYS: Union[List[str], str] = Field(default=[], env="GOOGLE_API_KEYS")
    GOOGLE_RPM: int = Field(default=20, env="GOOGLE_RPM")

    @field_validator("GOOGLE_API_KEYS", mode="before")
    @classmethod
    def split_comma_separated_string(cls, v):
        if isinstance(v, str) and not v.strip().startswith("["):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

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
