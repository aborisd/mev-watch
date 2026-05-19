from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    eth_ws_url: str
    eth_http_url: str

    database_url: str

    ingester_workers: int = 4
    block_confirmations: int = 2
    backfill_blocks: int = 0

    detector_interval_sec: int = 10
    min_net_profit_usd: float = 1.0

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "*"

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
