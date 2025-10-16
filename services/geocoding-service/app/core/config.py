from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GRPC_PORT: int = 50055

    TWOGIS_API_KEY: str = ""

    # Nizhny Novgorod boundaries
    NN_LAT_MIN: float = 56.20
    NN_LAT_MAX: float = 56.40
    NN_LON_MIN: float = 43.75
    NN_LON_MAX: float = 44.15

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
