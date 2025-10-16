from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GRPC_PORT: int = 50053

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/ai_tourist"

    WALK_SPEED_KMH: float = 4.0

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
