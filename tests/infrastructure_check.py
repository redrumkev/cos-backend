"""Infrastructure availability checker for smart test skipping."""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


async def check_postgres_availability() -> bool:
    """Check if PostgreSQL test database is available."""
    try:
        import asyncpg

        # Try multiple possible URL env vars, with DEV as fallback
        db_url = (
            os.getenv("POSTGRES_TEST_URL")
            or os.getenv("DATABASE_URL_TEST")
            or os.getenv("DATABASE_URL_DEV")
            or "postgresql://cos_user:Police9119%21%21Sql_dev@localhost:5433/cos_db_dev"  # URL-encoded fallback
        )

        # Convert SQLAlchemy URL to asyncpg format if needed
        if "+asyncpg" in db_url:
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

        conn = await asyncpg.connect(db_url)
        await conn.close()
        return True
    except Exception as e:
        logger.debug(f"PostgreSQL check failed: {e}")
        return False


def check_neo4j_availability() -> bool:
    """Check if Neo4j is available."""
    try:
        import httpx

        neo4j_uri = "http://localhost:7474"
        response = httpx.get(neo4j_uri, timeout=5)
        return bool(response.status_code == 200)
    except Exception as e:
        logger.debug(f"Neo4j check failed: {e}")
        return False


def check_redis_availability() -> bool:
    """Check if Redis is available."""
    try:
        import redis

        # Try both localhost (for local development) and redis (for docker)
        redis_hosts = [os.getenv("REDIS_HOST", "localhost"), "localhost"]
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD", "Police9119!!Red")  # fallback to known password

        for host in redis_hosts:
            try:
                r = redis.Redis(host=host, port=redis_port, password=redis_password, decode_responses=True)
                r.ping()
                logger.debug(f"Redis connection successful on {host}:{redis_port}")
                return True
            except Exception as host_e:
                logger.debug(f"Redis check failed for {host}:{redis_port} - {host_e}")
                continue

        return False
    except Exception as e:
        logger.debug(f"Redis check failed: {e}")
        return False


def get_available_services() -> dict[str, bool]:
    """Get dictionary of available services."""
    services = {
        "postgres": asyncio.run(check_postgres_availability()),
        "neo4j": check_neo4j_availability(),
        "redis": check_redis_availability(),
    }

    logger.info(f"Available services: {services}")
    return services


# Initialize available services on import
AVAILABLE_SERVICES = get_available_services()
