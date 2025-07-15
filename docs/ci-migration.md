# CI/CD Migration Guide

## Current State: Local Pre-commit Only

As of January 11, 2025, the COS project has transitioned to a local-only development workflow using pre-commit hooks. All GitHub Actions workflows have been archived at `/docs/archive/github-actions/`.

### Active Development Workflow

1. **Pre-commit Hooks** (Mandatory):
   - Ruff linting and formatting
   - MyPy type checking
   - Bandit security scanning
   - File integrity checks (YAML, TOML, merge conflicts)
   - Large file prevention
   - Private key detection

2. **Local Testing**:
   ```bash
   # Run all tests with coverage
   uv run pytest --cov=src --cov-report=html --cov-report=term

   # Run specific test categories
   uv run pytest -m "unit"
   uv run pytest -m "integration"
   uv run pytest -m "not slow"
   ```

3. **Manual Quality Checks**:
   ```bash
   # Run pre-commit on all files
   uv run pre-commit run --all-files

   # Run specific hooks
   uv run pre-commit run ruff --all-files
   uv run pre-commit run mypy --all-files
   ```

## GitLab CI Migration Plan

### Phase 1: Infrastructure Setup (Week 1)
1. **Mac Studio Runner Configuration**:
   - Install GitLab Runner on Mac Studio
   - Configure as Docker executor
   - Set up runner tags: `mac-studio`, `docker`, `high-memory`
   - Resource allocation: 8 CPU cores, 32GB RAM

2. **GitLab Project Setup**:
   - Create GitLab project mirror
   - Configure Container Registry
   - Set up environment variables
   - Configure protected branches

### Phase 2: Basic Pipeline (Week 2)
1. **`.gitlab-ci.yml` Structure**:
   ```yaml
   stages:
     - validate
     - test
     - integration
     - performance
     - security
     - deploy

   variables:
     UV_CACHE_DIR: $CI_PROJECT_DIR/.uv-cache
     DOCKER_DRIVER: overlay2
     DOCKER_TLS_CERTDIR: "/certs"
   ```

2. **Essential Jobs**:
   - Code quality (ruff, mypy, bandit)
   - Unit tests with coverage
   - Integration tests with services
   - Performance benchmarks

### Phase 3: Advanced Features (Week 3-4)
1. **Parallel Execution**:
   - Split tests by module
   - Concurrent service testing
   - Matrix testing for Python versions

2. **Caching Strategy**:
   - UV package cache
   - Docker layer cache
   - Test result cache
   - Benchmark baselines

3. **Merge Request Pipelines**:
   - Automated review apps
   - Preview deployments
   - Incremental testing

## Resource Requirements for Mac Studio

### Minimum Specifications
- **CPU**: 8+ cores for parallel job execution
- **RAM**: 32GB (services + tests + caching)
- **Storage**: 500GB SSD (Docker images + caches)
- **Network**: Gigabit connection for registry operations

### Recommended Configuration
- **CPU**: 12-16 cores
- **RAM**: 64GB
- **Storage**: 1TB NVMe SSD
- **Docker**: Latest stable version
- **GitLab Runner**: Latest stable version

### Service Requirements
Each CI run will need:
- PostgreSQL: 2GB RAM
- Redis: 1GB RAM
- Neo4j: 4GB RAM
- Python environments: 2GB per job
- Docker overhead: 4GB

Total peak memory: ~20GB for full pipeline

## Suggested GitLab Pipeline Structure

### 1. Validation Stage (Fast Feedback)
```yaml
validate:lint:
  stage: validate
  script:
    - uv run ruff check .
    - uv run ruff format . --check
  rules:
    - if: $CI_MERGE_REQUEST_ID

validate:types:
  stage: validate
  script:
    - uv run mypy src/
  rules:
    - if: $CI_MERGE_REQUEST_ID
```

### 2. Test Stage (Parallel Execution)
```yaml
test:unit:
  stage: test
  parallel:
    matrix:
      - MODULE: [cc, graph, common]
  script:
    - uv run pytest tests/backend/$MODULE -m "unit"
  coverage: '/TOTAL.*\s+(\d+%)/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

test:integration:
  stage: test
  services:
    - postgres:17.5
    - redis:7.2
    - neo4j:5.15
  script:
    - uv run pytest -m "integration"
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    - if: $CI_MERGE_REQUEST_ID
```

### 3. Performance Stage
```yaml
performance:benchmark:
  stage: performance
  script:
    - uv run pytest -m "benchmark" --benchmark-json=benchmark.json
  artifacts:
    paths:
      - benchmark.json
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    - if: $CI_MERGE_REQUEST_ID
      when: manual
```

### 4. Security Stage
```yaml
security:scan:
  stage: security
  script:
    - uv run bandit -r src/
    - uv run safety check
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

## Learnings from GitHub Actions Issues

### 1. Redis Configuration
**Problem**: Password authentication conflicts between environments
**Solution**: Standardize on NO PASSWORD for all non-production environments
**GitLab Implementation**: Use Redis service without authentication

### 2. Service Health Checks
**Problem**: Race conditions with service startup
**Solution**: Implement proper health check waiting
**GitLab Implementation**:
```yaml
before_script:
  - |
    for i in {1..30}; do
      if pg_isready -h postgres -U cos_user; then
        break
      fi
      echo "Waiting for PostgreSQL..."
      sleep 2
    done
```

### 3. Environment Variables
**Problem**: Inconsistent environment configuration
**Solution**: Use GitLab CI/CD variables with proper scoping
**GitLab Implementation**:
- Project-level variables for defaults
- Environment-specific variables for overrides
- Protected variables for sensitive data

### 4. Dependency Caching
**Problem**: Slow dependency installation
**Solution**: Aggressive caching with UV
**GitLab Implementation**:
```yaml
cache:
  key: "$CI_COMMIT_REF_SLUG"
  paths:
    - .uv-cache/
    - .venv/
```

### 5. Test Parallelization
**Problem**: Long test execution times
**Solution**: Module-based test splitting
**GitLab Implementation**: Use `parallel:matrix` for test distribution

## Migration Timeline

### Week 1: Foundation
- [ ] Set up Mac Studio with GitLab Runner
- [ ] Create GitLab project and configure basics
- [ ] Implement validation stage

### Week 2: Core Pipeline
- [ ] Implement test stages with parallelization
- [ ] Set up integration tests with services
- [ ] Configure caching strategies

### Week 3: Advanced Features
- [ ] Add performance benchmarking
- [ ] Implement security scanning
- [ ] Set up merge request pipelines

### Week 4: Optimization
- [ ] Fine-tune resource allocation
- [ ] Optimize job dependencies
- [ ] Implement deployment stages

## Best Practices for GitLab CI

1. **Use DAG (Directed Acyclic Graph)** for job dependencies
2. **Implement fail-fast** for quick feedback
3. **Use job templates** to reduce duplication
4. **Leverage GitLab's built-in features**:
   - Code Quality reports
   - Security scanning
   - Coverage visualization
   - Performance analytics

5. **Monitor pipeline efficiency**:
   - Track job duration trends
   - Identify bottlenecks
   - Optimize parallelization

## Rollback Plan

If GitLab CI implementation faces issues:
1. Continue using local pre-commit hooks
2. Reference archived GitHub Actions for patterns
3. Consider alternative CI solutions (Jenkins, Drone)
4. Maintain local-first development philosophy

## Success Criteria

GitLab CI migration is successful when:
- [ ] All tests run in under 10 minutes
- [ ] Zero false-positive failures
- [ ] Developers have visibility into all stages
- [ ] Caching reduces dependency installation to <30s
- [ ] Mac Studio utilization stays under 80%
- [ ] Merge request feedback is available within 5 minutes
