from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PostgreSQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str 
    DB_NAME: str = "task_manager"

    @property
    def DATABASE_URL(self) -> str:
        return (
            # psycopg вместо asyncpg: asyncpg падает с WinError 64 на Python 3.14 (Windows)
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # SQLite (для разработки и тестов)
    SQLITE_URL: str = "sqlite+aiosqlite:///tasks.db"

    # Режим: "postgres" или "sqlite"
    DATABASE_MODE: str = "sqlite"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()