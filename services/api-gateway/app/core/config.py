from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str = "production"
    METRICS_PORT: int = 9090
    EMBEDDING_SERVICE_URL: str = "embedding-service:50051"
    RANKING_SERVICE_URL: str = "ranking-service:50052"
    ROUTE_SERVICE_URL: str = "route-planner-service:50053"
    LLM_SERVICE_URL: str = "llm-service:50054"
    GEOCODING_SERVICE_URL: str = "geocoding-service:50055"
    POI_SERVICE_URL: str = "poi-service:50056"
    REDIS_URL: str = "redis://redis:6379/0"
    SHARE_TTL_SECONDS: int = 60 * 60 * 24 * 14
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
