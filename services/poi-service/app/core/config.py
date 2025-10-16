from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GRPC_PORT: int = 50056

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/ai_tourist"

    TWOGIS_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
