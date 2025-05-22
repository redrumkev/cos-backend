from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):  # type: ignore[misc]
    POSTGRES_DEV_URL: str = Field(
        default="postgresql://test:test@localhost/test_db",
        validation_alias="POSTGRES_DEV_URL",
    )
    POSTGRES_TEST_URL: str = Field(
        default="postgresql://test:test@localhost/test_test_db",
        validation_alias="POSTGRES_TEST_URL",
    )
    REDIS_HOST: str = Field(default="localhost", validation_alias="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, validation_alias="REDIS_PORT")
    REDIS_PASSWORD: str | None = Field(
        default="test_password", validation_alias="REDIS_PASSWORD"
    )
    MEM0_SCHEMA: str = Field(default="mem0_cc", validation_alias="MEM0_SCHEMA")

    model_config = {
        "env_file": "infrastructure/.env",
        "env_file_encoding": "utf-8",
        "extra": "allow",
    }

    @property
    def sync_db_url(self) -> str:
        return self.POSTGRES_DEV_URL

    @property
    def async_db_url(self) -> str:
        # Convert sync URL to asyncpg format if needed
        if self.POSTGRES_DEV_URL.startswith("postgresql://"):
            return self.POSTGRES_DEV_URL.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return self.POSTGRES_DEV_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()


# FastAPI dependency
async def get_settings_dep() -> Settings:
    return get_settings()
