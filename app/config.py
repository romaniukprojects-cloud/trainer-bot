from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str
    trainer_telegram_id: int
    database_url: str = "sqlite+aiosqlite:///./data/clients.db"
    timezone: str = "Europe/Kyiv"

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL for APScheduler's SQLAlchemyJobStore."""
        return self.database_url.replace("+aiosqlite", "")


settings = Settings()
