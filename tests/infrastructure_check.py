"""Infrastructure availability checker for smart test skipping."""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


async def check_postgres_availability() -> bool:
    """Check if PostgreSQL test database is available."""
    try:
        import asyncpg

        db_url = os.getenv("POSTGRES_TEST_URL") or os.getenv("DATABASE_URL_TEST")
        if not db_url:
            logger.debug("No PostgreSQL test URL found in environment")
            return False
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

        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD") or None

        r = redis.Redis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)
        r.ping()
        return True
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
