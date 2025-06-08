# COS Infrastructure Command Reference
# Raw commands for manual operation and future Docker containerization

## Core Commands

### Unified Startup (Zero Orphans)
```bash
# Navigate to infrastructure directory
cd G:\cos\infrastructure

# Start all services together (eliminates orphan warnings)
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml -f docker-compose.mem0g.yml up -d

# Wait for initialization
sleep 30

# Verify health
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Unified Shutdown
```bash
# Stop all services cleanly
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml -f docker-compose.mem0g.yml down --remove-orphans

# Verify shutdown
docker ps | grep cos_
```

### Service Health Checks
```bash
# Container status
docker ps --format "table {{.Names}}\t{{.Status}}" | grep cos_

# Network status
docker network ls | grep cos_network

# Service connectivity
curl -s http://localhost:8080 > /dev/null && echo "Traefik: OK" || echo "Traefik: FAIL"
curl -s http://localhost:7474 > /dev/null && echo "Neo4j: OK" || echo "Neo4j: FAIL"
```

### Redis Commands
```bash
# Secure connection (WORKING METHOD)
docker exec -e REDISCLI_AUTH="Police9119!!Red" cos_redis redis-cli ping

# Redis commands
docker exec -e REDISCLI_AUTH="Police9119!!Red" cos_redis redis-cli info
docker exec -e REDISCLI_AUTH="Police9119!!Red" cos_redis redis-cli set test "hello"
docker exec -e REDISCLI_AUTH="Police9119!!Red" cos_redis redis-cli get test
```

### PostgreSQL Commands
```bash
# Connect to dev database
docker exec -it cos_postgres_dev psql -U cos_user -d cos_db_dev

# Connect from host (requires psql client)
psql -h localhost -p 5433 -U cos_user -d cos_db_dev
```

### Service Logs
```bash
# View logs for specific service
docker logs cos_postgres_dev
docker logs cos_redis
docker logs cos_neo4j
docker logs cos_traefik
docker logs cos_elasticsearch

# Follow logs in real-time
docker logs -f cos_postgres_dev
```

## Network & Data

### Network Management
```bash
# Create network (if needed)
docker network create cos_network

# List networks
docker network ls

# Inspect network
docker network inspect cos_network
```

### Data Directories
```bash
# Check data preservation
ls -la P:\postgres_cos_dev
ls -la E:\redis_cos_data
ls -la F:\neo4j_cos_data
ls -la F:\elasticsearch_cos_data
```

## Service Access Points
- **Traefik Dashboard**: http://localhost:8080
- **Neo4j Browser**: http://localhost:7474 (neo4j / Police9119!!Neo)
- **PostgreSQL Dev**: localhost:5433 (cos_user / Police9119!!Sql_dev)
- **Redis**: docker exec -e REDISCLI_AUTH="Police9119!!Red" cos_redis redis-cli
- **Elasticsearch**: localhost:9200

## Troubleshooting

### Force Clean Restart
```bash
# Nuclear option: stop everything and remove containers
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml -f docker-compose.mem0g.yml down --remove-orphans --volumes

# Remove any remaining COS containers
docker rm -f $(docker ps -aq --filter "name=cos_")

# Remove cos_network if stuck
docker network rm cos_network

# Restart from clean state
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml -f docker-compose.mem0g.yml up -d
```

### Port Conflicts
```bash
# Check what's using ports
netstat -ano | findstr ":5432"
netstat -ano | findstr ":6379"
netstat -ano | findstr ":7474"
netstat -ano | findstr ":8080"
```

## Future Docker Containerization Notes

When building COS as its own Docker container, the startup sequence will be:
1. Ensure cos_network exists
2. Start all services with unified compose command
3. Wait for health checks to pass
4. Verify connectivity to all endpoints

The working Redis authentication pattern:
```dockerfile
# In future COS container Dockerfile
ENV REDISCLI_AUTH="Police9119!!Red"
RUN docker exec cos_redis redis-cli ping
```
