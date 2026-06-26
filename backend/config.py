from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    chroma_persist_dir: str = "./chroma_db"
    model_store_dir: str = "./model_store"
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "*"

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "protected_namespaces": ("settings_",),
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
