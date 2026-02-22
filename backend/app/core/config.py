from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "Dallas OTC Crypto Desk Dashboard API"
    database_url: str = "postgresql+asyncpg://otc_user:otc_pass@localhost:5432/otcdesk"
    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    rfq_min_expiry_seconds: int = 10
    rfq_max_expiry_seconds: int = 60
    market_tick_seconds: float = 1.5
    market_symbols: str = "BTC-USD,ETH-USD,SOL-USD,ADA-USD"
    allowed_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def market_symbols_list(self) -> list[str]:
        return [item.strip() for item in self.market_symbols.split(",") if item.strip()]

    def allowed_origins_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]


settings = Settings()
