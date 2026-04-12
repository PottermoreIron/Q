from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/backtesting"
    redis_url: str = "redis://localhost:6379"
    api_secret_key: str = "dev-secret-change-in-production"
    environment: str = "development"

    # Auth (optional)
    google_client_id: str = ""
    google_client_secret: str = ""
    jwt_secret: str = "dev-jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # S3
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "backtesting"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"

    # Paid data source API keys (empty = connector disabled)
    polygon_api_key: str = ""
    alpha_vantage_api_key: str = ""
    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""
    alpaca_base_url: str = "https://data.alpaca.markets"


settings = Settings()
