# COS GitHub Actions CI Pipeline

## Overview

The GitHub Actions CI pipeline ensures zero-compromise quality control by mirroring local development gates in a fully automated environment. This document describes the workflow implementation and its alignment with the COS Constitution's Dual Mandate of 100% Quality and 100% Efficiency.

## Workflow Configuration

### Triggers
- **Push**: Runs on `main` and `develop` branches
- **Pull Request**: Runs against `main` and `develop` branches

### Python Support
- **Python 3.13**: Full support with GitHub Actions `setup-python@v5`
- **Matrix Strategy**: Currently focused on Python 3.13 as specified in `pyproject.toml`

## Service Dependencies

The CI environment mirrors the local development stack with the following service containers:

### PostgreSQL Databases
- **Development DB**: `postgres:17.5-bookworm` on port `5433`
  - Database: `cos_dev`
  - User: `postgres` / Password: `dev_password`

- **Test DB**: `postgres:17.5-bookworm` on port `5434`
  - Database: `cos_test`
  - User: `postgres` / Password: `test_password`

### Neo4j Graph Database
- **Image**: `neo4j:5`
- **Ports**: `7687` (Bolt), `7474` (HTTP)
- **Auth**: `neo4j/test_password`
- **Memory**: Optimized for CI with 512M max heap

### Redis Cache & Pub/Sub
- **Image**: `redis/redis-stack:latest`
- **Port**: `6379`
- **Auth**: `test_password`

## Pipeline Steps

### 1. Environment Setup
- Checkout code with `actions/checkout@v4`
- Install Python 3.13 with `actions/setup-python@v5`
- Install `uv` package manager for high-performance dependency resolution
- Cache pip dependencies for faster builds

### 2. Dependency Installation
```bash
uv pip install --system -e ".[dev]"
```
Installs all development dependencies including test frameworks, linting tools, and type checkers.

### 3. Service Health Verification
Validates all service containers are ready:
- PostgreSQL: `pg_isready` checks on both ports
- Neo4j: HTTP endpoint availability check
- Redis: `ping` command verification

### 4. Database Migrations
```bash
alembic upgrade head
```
Applies all Alembic migrations to both development and test databases, ensuring schema consistency.

### 5. Pre-commit Quality Gates
```bash
pre-commit run --all-files
```
Executes all configured pre-commit hooks:
- **Ruff**: Linting and formatting with `--fix` and `--exit-non-zero-on-fix`
- **MyPy**: Strict type checking with Python 3.13 configuration
- **Bandit**: Security vulnerability scanning
- **Standard Hooks**: YAML/TOML validation, trailing whitespace, large file detection

### 6. Test Execution with Coverage
```bash
pytest -q --cov=src --cov=scripts --cov-report=xml --cov-report=term --cov-fail-under=97
```

#### Coverage Requirements
- **Minimum**: 97% coverage (hard requirement)
- **Scope**: `src/` and `scripts/` directories
- **Output**: XML report for Codecov, terminal summary for immediate feedback
- **Fail Fast**: Pipeline fails immediately if coverage drops below threshold

### 7. Coverage Reporting (Optional)
Uploads coverage data to Codecov if `CODECOV_TOKEN` secret is configured.

## Environment Variables

The CI environment sets comprehensive environment variables:

```bash
DATABASE_URL_DEV=postgresql+asyncpg://postgres:dev_password@localhost:5433/cos_dev
DATABASE_URL_TEST=postgresql+asyncpg://postgres:test_password@localhost:5434/cos_test
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=test_password
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=test_password
TESTING=true
ENVIRONMENT=test
```

## Alignment with COS Principles

### Frictionless Workflow
- Zero configuration required for contributors
- Mirrors local development environment exactly
- Fast feedback loop with parallel service startup

### Quality Gates Enforcement
- **Pre-commit hooks**: Automated code quality and security checks
- **Type safety**: MyPy with strict configuration
- **Test coverage**: 97% minimum threshold with fail-fast behavior
- **Migration safety**: Database schema consistency validation

### Relentless Evolution
- Uses latest stable images (PostgreSQL 17.5, Neo4j 5)
- Modular service configuration for easy updates
- Comprehensive logging and health checks

## Performance Optimizations

### Caching Strategy
- **pip cache**: Enabled via `actions/setup-python@v5`
- **uv installation**: Fast Rust-based package manager
- **Service containers**: Optimized memory settings for CI environment

### Parallel Execution
- Service containers start in parallel
- Health checks run concurrently
- Test execution uses `pytest-xdist` for parallel testing

## Troubleshooting

### Service Connection Issues
If services fail to connect:
1. Check service health in workflow logs
2. Verify port mappings match local configuration
3. Ensure environment variables are correctly set

### Coverage Failures
If coverage drops below 97%:
1. Identify uncovered code in terminal output
2. Add missing tests for new functionality
3. Update coverage exclusions in `pyproject.toml` if justified

### Migration Failures
If Alembic migrations fail:
1. Check migration script syntax
2. Verify database schema compatibility
3. Ensure proper dependency order

## Security Considerations

- **No secrets in workflow**: All passwords are test-only values
- **Bandit scanning**: Automated security vulnerability detection
- **Private key detection**: Pre-commit hook prevents accidental commits
- **Dependency scanning**: Future enhancement for supply chain security

## Future Enhancements

- **Matrix builds**: Expand to multiple Python versions if needed
- **Performance benchmarks**: Integration with `pytest-benchmark`
- **Security scanning**: Enhanced vulnerability detection
- **Self-hosted runners**: For improved performance and control
