# COS - Creative Operating System

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![Code Coverage](https://img.shields.io/badge/coverage-86%25-brightgreen.svg)](https://github.com/redrumkev/cos-backend)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

COS (Creative Operating System) is a toolkit built to serve a 100+ book legacy vision. This system represents the translation of life-student insights into a technical foundation for creating classic non-fiction works.

## Overview

COS implements a sophisticated multi-layer memory system designed for creative workflows:
- **L1 (PostgreSQL)**: Immediate storage with mem0 integration
- **L1.5 (Redis)**: Real-time pub/sub event highway
- **L2 (Neo4j)**: Graph relationships and semantic connections
- **L3 (ZK)**: Curated knowledge layer (planned)
- **L4 (Canonical)**: Immutable archival storage

The system follows FORWARD principles: Frictionless, Orchestrated, Real-Time, Wide-Angle, Adaptive, Relentless, and Destiny-Driven.

## 🚀 Local Development Workflow

This project uses a **local-first development approach** with mandatory pre-commit hooks to ensure code quality before commits.

### Setting Up Pre-commit Hooks (Required)

Pre-commit hooks are **mandatory** for all development. They ensure code quality standards are met before any commit reaches the repository.

```bash
# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Verify installation
uv run pre-commit --version

# Run hooks manually on all files
uv run pre-commit run --all-files

# Run hooks on specific files
uv run pre-commit run --files src/backend/cc/router.py
```

### What Pre-commit Checks

Every commit automatically runs:
- **Ruff**: Linting and auto-formatting (fixes on commit)
- **MyPy**: Static type checking
- **Bandit**: Security vulnerability scanning
- **File Checks**: YAML/TOML validation, large file prevention, private key detection
- **Code Hygiene**: Trailing whitespace, EOF fixes, merge conflict detection

### Development Commands

```bash
# Run all tests with coverage
uv run pytest --cov=src --cov-report=html --cov-report=term

# Run specific test types
uv run pytest -m "unit"                    # Unit tests only
uv run pytest -m "integration"             # Integration tests
uv run pytest -m "not slow"                # Skip slow tests

# Manual quality checks
uv run ruff check .                        # Linting
uv run ruff format .                       # Formatting
uv run mypy src/                           # Type checking
uv run bandit -r src/                      # Security scanning
```

### Troubleshooting Pre-commit

If you encounter issues:

1. **"pre-commit not found"**: Ensure you're in the project virtual environment:
   ```bash
   source .venv/bin/activate  # or use UV's environment
   ```

2. **Hook failures**: Pre-commit will show exactly what failed. Common fixes:
   ```bash
   # Let Ruff auto-fix issues
   uv run ruff check . --fix
   uv run ruff format .

   # Check MyPy errors
   uv run mypy src/ --show-error-codes
   ```

3. **Bypass hooks** (emergency only, not recommended):
   ```bash
   git commit --no-verify -m "Emergency commit"
   ```

### CI/CD Status

This project currently uses **local-only quality checks** via pre-commit hooks. GitHub Actions have been archived in preparation for a future GitLab CI migration. See [CI Migration Guide](docs/ci-migration.md) for details.
