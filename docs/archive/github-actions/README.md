# Archived GitHub Actions Workflows

## Archive Date: January 11, 2025

## Why These Were Archived

These GitHub Actions workflows were archived as part of the migration to a local-only development workflow with pre-commit hooks. The project is transitioning away from GitHub CI/CD to prepare for a future GitLab CI implementation.

### Reasons for Archival:
1. **CI Infrastructure Issues**: The GitHub Actions workflows were experiencing persistent failures due to:
   - Redis connection issues in CI environment
   - Password authentication conflicts between local and CI environments
   - Resource constraints in GitHub's free tier

2. **Development Philosophy**: Moving to local-first development with pre-commit hooks ensures:
   - Faster feedback loops for developers
   - No dependency on external CI infrastructure
   - Consistent development experience across all environments

3. **Future Migration**: These workflows are preserved to aid in the future GitLab CI migration, providing:
   - Reference for test configurations
   - Patterns for parallel job execution
   - Environment setup requirements

## Archived Workflows

### ci.yml
- **Purpose**: Main CI pipeline for unit tests, linting, and code quality checks
- **Key Features**:
  - Python 3.13 setup
  - UV package manager integration
  - Ruff linting and formatting
  - MyPy type checking
  - Bandit security scanning
  - Pytest with coverage reporting
- **Useful Patterns**: Matrix testing strategy, caching dependencies

### integration.yml
- **Purpose**: Integration tests with real infrastructure
- **Key Features**:
  - Docker Compose service orchestration
  - PostgreSQL, Redis, and Neo4j setup
  - Health check waiting logic
  - Environment variable configuration
- **Useful Patterns**: Service dependency management, health check implementation

### performance.yml
- **Purpose**: Performance benchmarking and regression detection
- **Key Features**:
  - Pytest benchmark plugin usage
  - Performance threshold validation
  - Benchmark result storage
- **Useful Patterns**: Performance baseline comparison

### redis-integration.yml
- **Purpose**: Dedicated Redis pub/sub integration testing
- **Key Features**:
  - Redis-specific test configuration
  - Circuit breaker testing
  - Pub/sub pattern validation
- **Useful Patterns**: Redis connection handling, fault tolerance testing

## Lessons Learned for GitLab Migration

1. **Environment Consistency**: Ensure local and CI environments use identical configurations
2. **Service Dependencies**: Use Docker Compose for consistent service setup
3. **Caching Strategy**: Implement aggressive caching for dependencies (UV cache, Docker layers)
4. **Parallel Execution**: Separate unit, integration, and performance tests into parallel jobs
5. **Resource Requirements**: Plan for adequate memory/CPU for Mac Studio runners
6. **Secret Management**: Use GitLab's native secret management instead of environment files

## Migration Notes

When implementing GitLab CI, consider:
- Using GitLab's Docker-in-Docker service for integration tests
- Implementing manual approval gates for deployment stages
- Setting up GitLab Container Registry for custom images
- Using GitLab's built-in coverage visualization
- Leveraging merge request pipelines for efficient CI

These archived workflows remain available for reference but are no longer active in the development process.
