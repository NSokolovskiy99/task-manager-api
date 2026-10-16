from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # PostgreSQL
    DB_HOST: str | None = None  # <-- было "localhost", теперь None
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str
    DB_NAME: str = "task_manager"

    DATABASE_MODE: str = "sqlite"

    @property
    def DATABASE_URL(self) -> str:
        # Если DB_HOST задан (например, host.docker.internal) — берём его.
        # Иначе fallback на localhost (для совсем локального запуска без Docker).
        host = self.DB_HOST or "localhost"
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{host}:{self.DB_PORT}/{self.DB_NAME}"
        )

    SQLITE_URL: str = "sqlite+aiosqlite:///tasks.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

settings = Settings()