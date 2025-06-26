## **003_testing_requirements.md**
```markdown
# Testing Standards & Requirements

## Coverage Requirements (Non-Negotiable)
- **Unit Test Coverage**: ≥ 97% for new/modified code
- **Overall Project Coverage**: ≥ 90%
- **Performance Tests**: All critical paths benchmarked

## Test Structure
tests/
├── unit/           # Mock all external deps (DB, Redis, APIs)
├── integration/    # Use live services (Docker containers)
├── performance/    # pytest-benchmark for latency validation
└── api/           # End-to-end API testing

## Unit Test Patterns
```python
# Async database mocking
@pytest.fixture
async def mock_db_session():
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session

# Redis mocking
@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.publish = AsyncMock()
    return redis

# Logfire mocking
@pytest.fixture
def mock_logfire():
    with patch('logfire.span') as mock_span:
        yield mock_span
Performance Benchmarks
python# Example latency test
@pytest.mark.benchmark(group="database")
async def test_log_l1_performance(benchmark, db_session):
    result = await benchmark(log_l1, db_session, test_data)
    assert result.extra_info['latency_ms'] < 2.0  # p95 < 2ms
Test Execution
bash# Full test suite with coverage
pytest --cov --cov-fail-under=97

# Performance tests only
pytest -m benchmark

# Integration tests only
pytest tests/integration/
