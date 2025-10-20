from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GRPC_PORT: int = 50053

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/ai_tourist"

    WALK_SPEED_KMH: float = 4.0
    TRANSIT_DISTANCE_THRESHOLD_KM: float = 2.0

    TWOGIS_API_KEY: str | None = None
    NAVITIA_API_KEY: str | None = None
    REDIS_URL: str = "redis://redis:6379/0"
    ROUTING_CACHE_TTL_SECONDS: int = 3600

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
