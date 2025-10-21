from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GRPC_PORT: int = 50054
    METRICS_PORT: int = 9090

    LLM_PROVIDER: str = "anthropic"  # anthropic or openai
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
