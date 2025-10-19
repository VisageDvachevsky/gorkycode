from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    GRPC_PORT: int = 50053

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/ai_tourist"

    REDIS_URL: str = "redis://redis:6379/0"
    TWOGIS_API_KEY: str | None = None
    NAVITIA_API_KEY: str | None = None

    DEFAULT_WALK_SPEED_KMH: float = 4.5
    TRANSIT_DISTANCE_THRESHOLD_KM: float = 2.0


settings = Settings()
