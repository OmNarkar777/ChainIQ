from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://chainiq:chainiq@localhost:5432/chainiq"
    sync_database_url: str = "postgresql://chainiq:chainiq@localhost:5432/chainiq"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    chroma_persist_dir: str = "./chroma_db"
    model_store_dir: str = "./model_store"
    app_env: str = "development"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
