from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GRPC_PORT: int = 50051
    
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    REDIS_URL: str = "redis://redis:6379/0"
    CACHE_TTL_SECONDS: int = 86400  # 24 hours
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()