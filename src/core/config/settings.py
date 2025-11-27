from pydantic_settings import BaseSettings

class AppConfig(BaseSettings):
    # API configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001

    # Celery configuration
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Database configuration
    DATABASE_URL: str = "postgresql+psycopg://user:password@postgres:5432/dev_agent_db"

    # LLM Provider configuration
    LLM_PROVIDER: str = "google"  # "openai", "anthropic", "google"
    GOOGLE_API_KEY: str = "your_google_api_key"
    OPENAI_API_KEY: str = "your_openai_api_key"
    ANTHROPIC_API_KEY: str = "your_anthropic_api_key"

    # Workspace configuration (path inside the container)
    WORKSPACE_PATH: str = "/app/workspace"
    HOST_WORKSPACE_PATH: str = "./workspace" # Local path to mount

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = AppConfig()
