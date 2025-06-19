from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Legal AI Assistant"

    # Database Settings
    CHROMA_DB_PATH: str = "data/legal_db"

    # Model Settings
    EMBEDDING_MODEL: str = "mxbai-embed-large"
    CHAT_MODEL: str = "llama3.2"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Data Settings
    DATA_DIR: str = "data/legal_documents"
    RAW_DATA_DIR: str = "data/raw"
    PROCESSED_DATA_DIR: str = "data/processed"

    # API Keys (to be loaded from environment variables)
    OPENAI_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
