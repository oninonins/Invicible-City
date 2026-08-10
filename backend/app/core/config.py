from typing import List

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "secret"
    PROJECT_NAME: str = "Invisible City MVP"
    
    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:3000"]'
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000"]
    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8 # 8 days

    DATABASE_URL: str = ""
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "sdgs"
    POSTGRES_PORT: str = "5432"
    
    REDIS_HOST: str = "redis"
    REDIS_PORT: str = "6379"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "meta-llama/llama-3.1-8b-instruct:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


settings = Settings()
