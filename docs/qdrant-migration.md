# Qdrant Vector Database Migration Guide

## Overview

Qdrant is being added to the COS infrastructure to provide vector storage and similarity search capabilities. This document outlines the migration path from optional to required status.

## Why Qdrant?

Qdrant is being added to support:
- **Vector Storage**: Store embeddings from LLM-generated content
- **Similarity Search**: Find semantically similar content across the system
- **Memory Enhancement**: Improve mem0 integration with vector-based retrieval
- **Scalability**: Handle growing vector data needs as COS expands

## Current Status (Sprint 2)

- **Status**: Optional service with graceful fallbacks
- **Integration**: Available in CC module via `vector_service.py`
- **Health Check**: Integrated into enhanced health endpoint
- **Fallback**: All vector operations return None/empty when Qdrant unavailable

## How to Enable Qdrant Now

1. **Uncomment Docker Service**:
   ```bash
   # Edit infrastructure/docker-compose.yml
   # Uncomment the entire qdrant service block (lines 167-207)
   ```

2. **Uncomment Override Configuration**:
   ```bash
   # Edit infrastructure/docker-compose.override.yml
   # Uncomment the qdrant override block (lines 44-58)
   ```

3. **Create Data Directory**:
   ```bash
   mkdir -p ~/cos-data/qdrant/prod
   ```

4. **Start Qdrant**:
   ```bash
   cd infrastructure/
   docker-compose up -d qdrant
   ```

5. **Verify Health**:
   ```bash
   # Check Qdrant directly
   curl http://localhost:6333/health

   # Check via CC enhanced health endpoint
   curl http://localhost:8000/cc/health/enhanced | jq .qdrant_status
   ```

## Features That Use Qdrant

Currently (when available):
- Vector storage in CC module (`store_vector`)
- Similarity search (`search_similar`)
- Vector deletion (`delete_vector`)

Future features requiring Qdrant:
- Semantic memory retrieval in mem0
- Cross-module similarity matching
- Content deduplication
- Recommendation engine
- Advanced search capabilities

## Migration Timeline

### Sprint 2 (Current)
- ✅ Qdrant configuration added (commented out)
- ✅ Graceful fallback implementation
- ✅ Health check integration
- ✅ Basic vector operations in CC module

### Sprint 3 (Next)
- [ ] Make Qdrant required service
- [ ] Remove fallback logic from `qdrant_config.py`
- [ ] Update health checks to degrade when unavailable
- [ ] Add Qdrant to CI/CD pipeline
- [ ] Implement vector operations in mem0

### Sprint 4 (Future)
- [ ] Cross-module vector search
- [ ] Advanced similarity algorithms
- [ ] Vector index optimization
- [ ] Performance benchmarking

## Code Changes Required for Sprint 3

1. **Remove Graceful Fallbacks**:
   - Update `qdrant_config.py` to raise exceptions instead of returning None
   - Remove `is_available()` checks from vector_service
   - Update health check to mark service as degraded without Qdrant

2. **Update Docker Configuration**:
   - Uncomment Qdrant service in docker-compose files
   - Add to required services list in startup scripts

3. **Update Tests**:
   - Remove skip markers for Qdrant-dependent tests
   - Add integration tests for vector operations
   - Update CI to include Qdrant container

4. **Update Documentation**:
   - Mark Qdrant as required in README
   - Update infrastructure setup guides
   - Document vector operation APIs

## Configuration Options

### Environment Variables
```bash
QDRANT_HOST=localhost      # Qdrant server host
QDRANT_PORT=6333          # REST API port
QDRANT_GRPC_PORT=6334     # gRPC port (optional)
QDRANT_API_KEY=           # Production API key (optional)
```

### Resource Allocation
- **MacBook Air M4**: 1GB RAM reserve, 2GB limit, 1 CPU
- **Mac Studio M4 Max**: 4GB RAM reserve, 8GB limit, 2 CPUs

### Collection Configuration
Default collection: `cc_vectors`
- Vector size: 1536 (OpenAI ada-002)
- Distance metric: Cosine
- TODO: Make configurable based on embedding model

## Troubleshooting

### Qdrant Not Starting
```bash
# Check logs
docker logs cos_qdrant

# Verify port availability
lsof -i :6333

# Check data directory permissions
ls -la ~/cos-data/qdrant/
```

### Connection Failures
```bash
# Test direct connection
curl http://localhost:6333/health

# Check from within Docker network
docker exec cos_backend curl http://qdrant:6333/health
```

### Performance Issues
- Monitor memory usage: `docker stats cos_qdrant`
- Check collection size: Use Qdrant dashboard at http://localhost:6333/dashboard
- Review index configuration for large datasets

## References

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Qdrant Python Client](https://github.com/qdrant/qdrant-client)
- [Vector Database Comparison](https://qdrant.tech/benchmarks/)
