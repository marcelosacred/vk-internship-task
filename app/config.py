import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "botfarm"
    db_user: str = "postgres"
    db_password: str = "postgres"
    user_lock_ttl_seconds: int = 300

    @property
    def db_url(self) -> str:
        db_url = os.getenv("DB_URL") # для тестов
        if db_url:
            return db_url

        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
