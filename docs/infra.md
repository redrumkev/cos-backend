# COS Infrastructure Resource Management

## Overview

This document outlines the Docker resource allocation strategy for the Creative Operating System (COS) infrastructure. The configuration supports two primary development environments with explicit resource limits to ensure predictable performance.

## Target Environments

### 1. MacBook Air M4 (24GB RAM)
- **Total Docker RAM Cap**: 8GB
- **CPU Cores**: 8 (Apple M4)
- **Allocation Strategy**: Conservative to ensure smooth development alongside other applications

### 2. Mac Studio M4 Max (128GB RAM) - Future
- **Total Docker RAM Cap**: 32GB
- **CPU Cores**: 14 (Apple M4 Max)
- **Allocation Strategy**: Generous allocations for production-like performance

## Resource Allocation Summary

### MacBook Air M4 (24GB) Configuration

| Service | CPU Limit | CPU Reserve | RAM Limit | RAM Reserve | Notes |
|---------|-----------|-------------|-----------|-------------|-------|
| PostgreSQL (prod) | 4 cores | 2 cores | 3GB | 2GB | Primary database |
| PostgreSQL (dev) | 2 cores | 1 core | 2GB | 1GB | Development database |
| Redis | 2 cores | 0.5 cores | 1GB | 512MB | Mostly single-threaded |
| Elasticsearch | 4 cores | 2 cores | 3GB | 2GB | JVM heap: 2GB |
| Neo4j | 4 cores | 2 cores | 3GB | 2GB | Heap: 1GB, Pagecache: 1GB |
| Traefik | 1 core | 0.25 cores | 512MB | 256MB | Lightweight proxy |
| **Total** | - | **7.75 cores** | **12.5GB** | **7.75GB** | Within 8GB typical usage |

### Mac Studio M4 Max (128GB) Configuration - Scaling Guide

| Service | CPU Limit | CPU Reserve | RAM Limit | RAM Reserve | Notes |
|---------|-----------|-------------|-----------|-------------|-------|
| PostgreSQL (prod) | 8 cores | 4 cores | 12GB | 8GB | Scale with data |
| PostgreSQL (dev) | 4 cores | 2 cores | 8GB | 4GB | Generous dev environment |
| Redis | 4 cores | 1 core | 4GB | 2GB | Scale for caching |
| Elasticsearch | 8 cores | 4 cores | 6GB | 4GB | JVM heap: 4GB |
| Neo4j | 8 cores | 4 cores | 6GB | 4GB | Heap: 2GB, Pagecache: 2GB |
| Traefik | 2 cores | 0.5 cores | 1GB | 512MB | Still lightweight |
| **Total** | - | **15.5 cores** | **37GB** | **22.5GB** | Within 32GB cap |

## Key Design Principles

### 1. Soft Limits Philosophy
- **Reservations**: Guaranteed minimum resources (soft limits)
- **Limits**: Maximum allowed resources (hard caps)
- **Behavior**: Containers can burst above reservations when resources are available
- **Warning**: System warns but doesn't hard-fail on resource shortage

### 2. Service-Specific Considerations

#### PostgreSQL
- Production gets more resources than development
- Configured for connection pooling and performance
- Separate instances for isolation

#### Redis
- Lower CPU allocation (mostly single-threaded)
- Memory-focused allocation for caching
- Configured without password per CI_FIX_PROGRESS.md

#### Elasticsearch
- JVM heap set to ~66% of container memory limit
- Leaves room for Lucene file system cache
- CPU-intensive for indexing operations

#### Neo4j
- Balanced heap and pagecache allocation
- Memory-intensive for graph traversals
- Higher startup time allowance (30s)

#### Traefik
- Minimal resources (efficient proxy)
- Handles all HTTP routing
- Quick health check intervals

## Environment-Specific Overrides

### Using Docker Compose Overrides

Create a `docker-compose.override.yml` in the infrastructure directory:

```yaml
# Example: Scale up for Mac Studio M4 Max
services:
  postgres_prod:
    deploy:
      resources:
        limits:
          cpus: "8"
          memory: 12G
        reservations:
          cpus: "4"
          memory: 8G

  elasticsearch:
    environment:
      - ES_JAVA_OPTS=-Xms4g -Xmx4g
    deploy:
      resources:
        limits:
          memory: 6G
```

### Environment Variables

Create environment-specific `.env` files:

```bash
# .env.macbook
COMPOSE_PROFILES=development
DOCKER_MEMORY_LIMIT=8G

# .env.studio
COMPOSE_PROFILES=production
DOCKER_MEMORY_LIMIT=32G
```

## Tuning Recommendations

### 1. Monitoring Resource Usage

```bash
# View current resource usage
docker stats

# Check container limits
docker inspect <container_name> | jq '.[0].HostConfig.Memory'

# Monitor over time
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### 2. Performance Optimization

#### When to Scale Up
- Consistent CPU usage >80% of limit
- Memory usage approaching limit with OOM kills
- Slow query performance in databases
- Elasticsearch/Neo4j timeout errors

#### When to Scale Down
- Consistent resource usage <30% of reservation
- Development environment with limited concurrent usage
- Testing or CI environments

### 3. Service-Specific Tuning

#### PostgreSQL
```yaml
# Tune shared_buffers based on available memory
environment:
  - POSTGRES_SHARED_BUFFERS=512MB  # 25% of container RAM
```

#### Redis
```yaml
# Adjust maxmemory policy
environment:
  - REDIS_MAXMEMORY=800mb
  - REDIS_MAXMEMORY_POLICY=allkeys-lru
```

#### Elasticsearch
```yaml
# Fine-tune JVM settings
environment:
  - "ES_JAVA_OPTS=-Xms2g -Xmx2g -XX:+UseG1GC"
```

## Troubleshooting

### Common Issues

1. **Container OOM Kills**
   - Check `docker inspect` for OOMKilled flag
   - Increase memory limits or optimize application

2. **Slow Performance**
   - Monitor with `docker stats`
   - Check if hitting CPU or memory limits
   - Review application logs for bottlenecks

3. **Failed Health Checks**
   - May indicate insufficient resources
   - Check startup times vs. health check intervals
   - Review container logs

### Debug Commands

```bash
# Check Docker system resources
docker system df
docker system info | grep -i memory

# Inspect container resource usage
docker inspect <container> | jq '.[] | {memory: .HostConfig.Memory, cpu: .HostConfig.CpuQuota}'

# View container processes
docker top <container>

# Check for OOM events
dmesg | grep -i "killed process"
journalctl -u docker | grep -i oom
```

## Best Practices

1. **Start Conservative**: Begin with lower limits and scale up based on monitoring
2. **Test Under Load**: Use load testing to validate resource allocations
3. **Regular Review**: Monitor and adjust allocations monthly
4. **Document Changes**: Update this document when changing allocations
5. **Environment Parity**: Keep dev/prod ratios consistent (e.g., dev = 50% of prod)

## Migration Guide

When moving between environments:

1. **Export current data**: Use volume backups
2. **Adjust resource allocations**: Update compose files
3. **Validate configuration**: Run `docker-compose config`
4. **Test incrementally**: Start one service at a time
5. **Monitor closely**: Watch resource usage for first 24 hours

## CI/CD Considerations

For GitHub Actions and CI environments:
- Use minimal resource allocations
- Consider using separate compose files
- Implement resource-based test categorization
- Use mock mode for integration tests

## Future Enhancements

1. **Kubernetes Migration**: Resource limits will translate to K8s resource requests/limits
2. **Auto-scaling**: Implement HPA based on metrics
3. **Monitoring Stack**: Add Prometheus/Grafana for resource tracking
4. **Resource Quotas**: Implement namespace-level quotas in K8s

---

**Last Updated**: January 2025
**Version**: 1.0
**Maintainer**: COS Infrastructure Team
