from typing import List
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "AI-Tourist API"
    VERSION: str = "0.2.0"
    API_V1_STR: str = "/api/v1"

    ENVIRONMENT: str = "development"
    
    DATABASE_URL: PostgresDsn
    REDIS_URL: str = "redis://redis:6379/0"
    
    TWOGIS_API_KEY: str | None = None
    NAVITIA_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    LLM_PROVIDER: str = "anthropic"
    LLM_MODEL: str = "claude-sonnet-4-20250514"
    
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    CACHE_TTL_SECONDS: int = 3600
    GEOCODING_CACHE_TTL_SECONDS: int = 86400
    ROUTING_CACHE_TTL_SECONDS: int = 3600

    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 30

    DEFAULT_WALK_SPEED_KMH: float = 4.5
    
    TRANSIT_DISTANCE_THRESHOLD_KM: float = 2.0
    COFFEE_SEARCH_RADIUS_KM: float = 0.5
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)


settings = Settings()