# 🚀 COS Preflight Checklist – `infrastructure/.preflight_checklist.md`

This checklist must be completed **before starting COS with Docker Compose**. It ensures the entire infrastructure stack (PostgreSQL, Redis, Neo4j, mem0, mem0g, Traefik) starts cleanly and modularly with no port, label, or config conflicts.

---

## ✅ STEP A: Finalize `.env` File

Located at: `G:/cos/infrastructure/.env`

Must include:

```dotenv
# Redis
REDIS_PASSWORD=your_redis_password

# PostgreSQL
POSTGRES_USER=cos_user
POSTGRES_PASSWORD_PROD=...
POSTGRES_PASSWORD_DEV=...
POSTGRES_PASSWORD_TEST=...

POSTGRES_DB_PROD=cos_db_prod
POSTGRES_DB_DEV=cos_db_dev
POSTGRES_DB_TEST=cos_db_test

# Ensure these ports are free on your host machine
POSTGRES_PORT_PROD=5432
POSTGRES_PORT_DEV=5433
POSTGRES_PORT_TEST=5434
REDIS_PORT=6379 # For Redis primary
REDIS_INSIGHT_PORT=8001 # For RedisInsight UI

# Neo4j
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

---

## ✅ STEP B: Update Compose Files to Use `.env`

Ensure:

    In docker-compose.yml:

        All postgres_* services correctly use ${POSTGRES_USER}, ${POSTGRES_PASSWORD_PROD/DEV/TEST}, ${POSTGRES_DB_PROD/DEV/TEST}, and ${POSTGRES_PORT_PROD/DEV/TEST}.

        redis service correctly uses ${REDIS_PORT} and ${REDIS_INSIGHT_PORT} for port mapping.

    In docker-compose.mem0g.yml:

        neo4j service uses NEO4J_AUTH: ${NEO4J_USER}/${NEO4J_PASSWORD}.

    In redis.conf (located at ./redis.conf):

        Contains the line requirepass ${REDIS_PASSWORD}. (Verify that the redis/redis-stack image entrypoint performs environment variable substitution in this .conf file).

---

## ✅ STEP C: Modular Traefik Labeling Strategy (Chosen)

Strategy: Modular files with embedded Traefik labels per service.

Check:

    docker-compose.traefik.yml:

        Defines the traefik service only.

        The traefik service is configured to use cos_network.

    docker-compose.mem0g.yml:

        mem0g service has correct Traefik labels for mem0g.cos.local.

        neo4j service has correct Traefik labels for neo4j.cos.local.

        Both services use cos_network.

        Top-level networks: cos_network: external: true name: cos_network is present.

    Main docker-compose.yml:

        Defines networks: cos_network: driver: bridge.

---

## ✅ STEP D: Verify `hosts` File (✓)

Located at: C:/Windows/System32/drivers/etc/hosts (or /etc/hosts on Linux/macOS)

Must contain (ensure no conflicting entries for these hostnames):

```
127.0.0.1 cos.local         # For the main COS backend (future)
127.0.0.1 mem0g.cos.local
127.0.0.1 redis.cos.local   # For RedisInsight via Traefik (if labeled)
127.0.0.1 neo4j.cos.local
# Add other *.cos.local entries as services are defined and labeled for Traefik
```

(Note: redis.cos.local requires Traefik labels on the RedisInsight port if you want to access it via this hostname. Currently, RedisInsight is accessed via localhost:8001 or <host-ip>:8001 as per docker-compose.yml direct port mapping).

---

## ✅ STEP E: Ensure Docker Desktop is Running

Verify Docker Desktop (or your Docker daemon) is active and functioning.

---

## ✅ STEP F: One-Time Docker Network Creation (If Necessary)

Generally, running the main docker-compose.yml first will create cos_network.
However, if starting a modular compose file first that declares cos_network as external, you might need:

```
# Run from G:/cos/infrastructure/
docker network create cos_network
```

(Only run this if docker-compose -f docker-compose.yml ... up -d hasn't been run yet or if you get network errors).

---

## ✅ STEP G: Startup Sequence

(Run all commands from G:/cos/infrastructure/)

1. Start Base Infrastructure & Traefik:

```
# Pull latest images for main services
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml pull

# Start main infrastructure (Postgres, Redis, Elasticsearch) and Traefik
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
```

2. Start Modular Services (as needed):

```
# Start mem0g & Neo4j
docker-compose -f docker-compose.mem0g.yml pull
docker-compose -f docker-compose.mem0g.yml up -d
```

---

✅ STEP H: Post-Startup Verification

- Traefik Dashboard: http://localhost:8080 - Check for routers and services.

- Services via Traefik (if up and labeled):
  - http://neo4j.cos.local (from docker-compose.mem0g.yml)
  - http://mem0g.cos.local (from docker-compose.mem0g.yml)

- Direct Port Access (Fallback/Verification):
  - mem0: http://localhost:7790
  - Neo4j Browser: http://localhost:7474
  - RedisInsight: http://localhost:${REDIS_INSIGHT_PORT} (e.g., http://localhost:8001)
  - Postgres Dev: Connect via DB client to localhost:${POSTGRES_PORT_DEV} (e.g., localhost:5433)

- Check Container Logs:

```
docker logs cos_traefik
docker logs cos_postgres_dev
docker logs cos_redis
docker logs cos_neo4j
docker logs cos_mem0g
# etc.
```
