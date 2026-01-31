from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/syncobsidian.db"
    
    # JWT
    secret_key: str = "change-this-secret-key-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 heures
    
    # Storage
    storage_path: str = "./data/storage"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    request_timeout_seconds: int = 30
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignorer les variables non définies (DUCKDNS_*, DOMAIN, etc.)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Créer les dossiers nécessaires
os.makedirs(os.path.dirname(settings.database_url.replace("sqlite+aiosqlite:///", "")), exist_ok=True)
os.makedirs(settings.storage_path, exist_ok=True)
