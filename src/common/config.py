import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ------------------------ dynamic dotenv loading -------------------------
# Priority: ENV_FILE (explicit)  > infrastructure/.env  > ignore
candidate = os.getenv("ENV_FILE") or str(Path(__file__).parents[2] / "infrastructure" / ".env")
if Path(candidate).exists():
    load_dotenv(candidate)


class Settings(BaseSettings):
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
    REDIS_PASSWORD: str | None = Field(default="test_password", validation_alias="REDIS_PASSWORD")
    MEM0_SCHEMA: str = Field(default="mem0_cc", validation_alias="MEM0_SCHEMA")

    # Neo4j Configuration (Task 11)
    NEO4J_URI: str = Field(default="bolt://localhost:7687", validation_alias="NEO4J_URI")
    NEO4J_USER: str = Field(default="neo4j", validation_alias="NEO4J_USER")
    NEO4J_PASSWORD: str = Field(default="test", validation_alias="NEO4J_PASSWORD")
    ENABLE_GRAPH_INTEGRATION: bool = Field(default=False, validation_alias="ENABLE_GRAPH_INTEGRATION")

    # Scratch Data Configuration (Task 10)
    SCRATCH_DEFAULT_TTL_DAYS: int = Field(default=7, ge=1, le=365)
    SCRATCH_CLEANUP_BATCH_SIZE: int = Field(default=1000, ge=100, le=10000)
    SCRATCH_ENABLE_AUTO_CLEANUP: bool = Field(default=True)

    # Multi-Schema Support (Living Patterns - service.py v2.1.0)
    # Future modules: cc.*, pem.*, aic.* schemas
    POSTGRES_CC_URL: str | None = Field(default=None, validation_alias="POSTGRES_CC_URL")
    POSTGRES_PEM_URL: str | None = Field(default=None, validation_alias="POSTGRES_PEM_URL")
    POSTGRES_AIC_URL: str | None = Field(default=None, validation_alias="POSTGRES_AIC_URL")

    model_config = SettingsConfigDict(env_file=None)  # dotenv loaded manually

    @property
    def sync_db_url(self) -> str:
        return self.POSTGRES_DEV_URL

    @property
    def async_db_url(self) -> str:
        # Convert sync URL to asyncpg format if needed
        if self.POSTGRES_DEV_URL.startswith("postgresql://"):
            return self.POSTGRES_DEV_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.POSTGRES_DEV_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()


# FastAPI dependency
async def get_settings_dep() -> Settings:
    return get_settings()
