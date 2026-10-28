from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Transaction Ledger API"
    database_url: str = "sqlite:///./ledger.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
