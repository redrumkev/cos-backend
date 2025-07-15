
---

**Updated `infrastructure/README.dev.cos.md`**

```markdown
# 🧠 COS Infrastructure – Developer README

Located: `~/dev/cos/infrastructure/`

This file documents how to set up, launch, and work with the **COS (Creative Operating System)** infrastructure stack. It serves as the foundational runtime environment for core backend services and memory components.

---

## 📝 Pre-requisites

**IMPORTANT:** Before starting any services, complete the `infrastructure/preflight_checklist.md`. This ensures your `.env` file, Docker Compose files, and local `hosts` file are correctly configured.

---

## 📦 Docker Compose Structure

COS uses **modular Docker Compose files**, allowing flexible startup and isolated service orchestration. All file paths are relative to this `infrastructure` directory.

`mem0` (L1 Ephemeral Memory) is now an internal Python module within the main `cos_backend` application (to be built) and utilizes the Redis service defined in `docker-compose.yml`. It no longer has its own Docker Compose file or container.

### Core Compose Files:

| File                          | Purpose                                                    | Key Services Defined                 |
|-------------------------------|------------------------------------------------------------|--------------------------------------|
| `docker-compose.yml`         | Base infrastructure services                               | PostgreSQL (Prod, Dev, Test), Redis, Elasticsearch |
| `docker-compose.traefik.yml` | Traefik reverse proxy (provides `*.cos.local` routing)   | Traefik                              |
| `docker-compose.mem0g.yml`   | L2 Graph Memory Layer API Service & DB                     | `mem0g` (FastAPI service), Neo4j     |

### Configuration Files:

| File            | Purpose                                      |
|-----------------|----------------------------------------------|
| `.env`          | Environment variables (passwords, ports, etc.) |
| `traefik.yml`   | Static Traefik configuration (entrypoints, providers) |
| `redis.conf`    | Redis server configuration                   |

### Platform Setup:

**macOS Development (Standard):**
- Run `./setup-platform.sh` to configure the environment
- Creates data directories under `~/cos-data/`
- Copies `.env.macos` to `.env`
- Configures platform-specific Docker mounts

**Note:** Windows development has been deprecated. Historical Windows configurations are archived in `docs/archive/windows-configs/`.

---

### 🚀 Startup Sequence (All Services)

(Run commands from `~/dev/cos/infrastructure/`)

1.  **Ensure `preflight_checklist.md` is completed.**
2.  **Pull images for all services:**
    ```bash
    docker-compose -f docker-compose.yml -f docker-compose.traefik.yml pull
    docker-compose -f docker-compose.mem0g.yml pull
    ```
3.  **Start all services in detached mode:**
    ```bash
    docker-compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
    docker-compose -f docker-compose.mem0g.yml up -d
    ```

### Selective Startup Examples:

-   **Base Infrastructure + Traefik only:**
    ```bash
    docker-compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
    ```
-   **`mem0g` service & Neo4j (requires `cos_network` to exist, usually from main compose):**
    ```bash
    docker-compose -f docker-compose.mem0g.yml up -d
    ```

### 🛑 Stopping Services:

-   **Stop all services defined in specific files (and remove containers):**
    ```bash
    docker-compose -f docker-compose.yml -f docker-compose.traefik.yml down
    docker-compose -f docker-compose.mem0g.yml down
    ```
-   **Stop all services and remove volumes (use with caution, deletes persistent data):**
    ```bash
    docker-compose -f ... down -v
    ```

---

### 🗺️ Port Map & Service Access

Refer to the `preflight_checklist.md` (Step H: Post-Startup Verification) for a list of Traefik URLs (e.g., `http://mem0g.cos.local`) and direct port access URLs.

**Key Default Ports (Host Machine):**
| Service           | Host Port(s)      | Traefik URL (Example)         | Notes                                           |
|-------------------|-------------------|-------------------------------|-------------------------------------------------|
| Traefik HTTP      | `80`              | (Routes to various `*.cos.local`) | Main entrypoint for services via Traefik        |
| Traefik Dashboard | `8080`            | `http://localhost:8080`       | View Traefik routers/services                 |
| PostgreSQL DEV    | `${POSTGRES_PORT_DEV}` (e.g., `5433`) | N/A                           | Direct DB access for development              |
| PostgreSQL TEST   | `${POSTGRES_PORT_TEST}` (e.g., `5434`) | N/A                           | Direct DB access for testing framework        |
| Redis             | `${REDIS_PORT}` (e.g., `6379`)      | N/A                           | Direct Redis access (used by internal `mem0` logic) |
| RedisInsight      | `${REDIS_INSIGHT_PORT}` (e.g., `8001`) | `http://redis.cos.local` *  | UI for Redis (requires Traefik label on RedisInsight port) |
| Neo4j HTTP        | `7474`            | `http://neo4j.cos.local`      | Neo4j Browser UI                              |
| Neo4j Bolt        | `7687`            | N/A                           | Neo4j driver connections                      |
| mem0g API         | (No direct port exposed)  | `http://mem0g.cos.local`      | L2 Memory API (access via Traefik)          |
| Elasticsearch     | `9200`            | N/A                           | Direct Elasticsearch access (Traefik optional) |

*Note on `redis.cos.local`: To access RedisInsight via `http://redis.cos.local`, you would need to add Traefik labels to the `redis` service in `docker-compose.yml` targeting its port `8001`. Currently, it's accessed via `http://localhost:${REDIS_INSIGHT_PORT}`.*

---

## 🔗 COS & Nexus Architecture

COS is the **internal** creative intelligence system. `mem0` (L1 memory) is an internal Python module utilizing Redis. `mem0g` (L2 memory) is a service interacting with Neo4j. COS will eventually interact with `Pipeline` (external publishing) and exist within the broader **NEXUS** concept.
- For now, COS development is self-contained.
- Future `Pipeline` integration will likely use separate Docker networks with defined API/messaging bridges.

---

## 🛠️ Troubleshooting Tips

- Run `docker ps` to check running containers.
- Check individual container logs: `docker logs <container_name_or_id>`.
- Verify `preflight_checklist.md` steps, especially `.env` and `hosts` file.
- Ensure no other applications are using the ports defined in `.env` or Docker Compose files.
- Check Traefik dashboard (`http://localhost:8080`) for routing issues.
- If issues related to L1 memory (`mem0`), check `cos_redis` logs and the `cos_backend` logs (once `cos_backend` is running and using the internal `mem0` module).

---

This README provides the essential information for developers to get the COS infrastructure running locally. For detailed architectural principles and development standards, refer to the main COS documentation set.
