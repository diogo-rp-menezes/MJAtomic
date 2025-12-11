from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator
from typing import Optional, Literal, List, Union

class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "devagent_db"
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    # URL is optional, built from components if not provided
    POSTGRES_URL: Optional[str] = None

    @model_validator(mode='after')
    def assemble_db_url(self):
        if not self.POSTGRES_URL:
            self.POSTGRES_URL = f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Vector DB
    PGVECTOR_COLLECTION_NAME: str = "code_collection"

    # LLM Global Configuration
    LLM_PROVIDER: Literal["google", "ollama", "local"] = "google"

    # API Keys & Rate Limiting
    # Pydantic Settings automatically maps env vars to fields by name
    GOOGLE_API_KEYS: Union[List[str], str] = Field(default=[])
    GOOGLE_RPM: int = Field(default=20)
    REQUEST_DELAY_SECONDS: float = Field(default=0.0)

    @field_validator("GOOGLE_API_KEYS", mode="before")
    @classmethod
    def split_comma_separated_string(cls, v):
        if isinstance(v, str) and not v.strip().startswith("["):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    # Specific Agents Configuration
    ARCHITECT_MODEL: str = "gemini-2.5-flash"

    FULLSTACK_MODEL: str = "gemini-2.5-flash"
    FULLSTACK_BASE_URL: Optional[str] = None

    TECH_LEAD_MODEL: str = "gemini-2.5-flash"

    # Embeddings
    EMBEDDING_PROVIDER: Literal["google", "ollama", "local"] = "google"
    GOOGLE_EMBEDDING_MODEL: str = "embedding-001"

    # Ollama / Local specific
    OLLAMA_BASE_URL: Optional[str] = None
    OLLAMA_EMBEDDING_URL: Optional[str] = None
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    LOCAL_LLM_API_KEY: Optional[str] = None

    # Generic Local LLM (LM Studio, etc)
    LOCAL_LLM_BASE_URL: Optional[str] = None

    # Workspace
    LOCAL_WORKSPACE_PATH: str = "./workspace"
    DEFAULT_PROJECT_PATH: str = "./workspace"

    # Static Files
    STATIC_DIR: str = "/app/static"
    STATIC_DIR_FALLBACK: str = "frontend/dist"

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
