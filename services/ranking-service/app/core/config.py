from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GRPC_PORT: int = 50052
    
    DATABASE_URL: str = "postgresql+asyncpg://aitourist:password@postgresql:5432/aitourist_db"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()