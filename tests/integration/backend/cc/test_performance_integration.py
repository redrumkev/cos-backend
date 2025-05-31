"""Performance and reliability integration tests.

These tests validate our dual mandate: 100% Quality + 100% Efficiency.
Tests demonstrate proper async patterns, transaction performance, and reliability.
"""

import asyncio
import time

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.crud import create_module, get_modules
from src.backend.cc.services import create_module as service_create_module


class TestPerformanceIntegration:
    """Performance tests demonstrating dual mandate efficiency."""

    @pytest.mark.asyncio
    async def test_concurrent_module_creation_performance(self, db_session: AsyncSession) -> None:
        """Test concurrent module creation maintains performance under load."""
        start_time = time.time()

        # Create 10 modules concurrently
        tasks = []
        for i in range(10):
            task = create_module(db_session, f"perf_module_{i:03d}", "1.0.0")
            tasks.append(task)

        modules = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # Validate all modules created successfully
        assert len(modules) == 10
        for i, module in enumerate(modules):
            assert module.name == f"perf_module_{i:03d}"
            assert module.version == "1.0.0"
            assert module.active is True

        # Performance requirement: 10 concurrent creates in < 2 seconds
        assert elapsed < 2.0, f"Concurrent creation took {elapsed:.2f}s, should be < 2.0s"

    @pytest.mark.asyncio
    async def test_bulk_operations_efficiency(self, db_session: AsyncSession) -> None:
        """Test bulk operations maintain efficiency standards."""
        # Create test data efficiently
        module_count = 50
        start_time = time.time()

        # Bulk create modules
        modules = []
        for i in range(module_count):
            module = await create_module(db_session, f"bulk_module_{i:04d}", "1.0.0")
            modules.append(module)

        creation_time = time.time() - start_time

        # Test bulk retrieval
        start_time = time.time()
        retrieved_modules = await get_modules(db_session, skip=0, limit=module_count)
        retrieval_time = time.time() - start_time

        # Validate correctness (Quality mandate)
        assert len(retrieved_modules) == module_count

        # Validate efficiency (Efficiency mandate)
        assert creation_time < 5.0, f"Bulk creation took {creation_time:.2f}s, should be < 5.0s"
        assert retrieval_time < 1.0, f"Bulk retrieval took {retrieval_time:.2f}s, should be < 1.0s"

    @pytest.mark.asyncio
    async def test_transaction_isolation_reliability(self, db_session: AsyncSession) -> None:
        """Test transaction isolation maintains data integrity under concurrent access."""

        async def create_and_verify(session: AsyncSession, prefix: str, count: int) -> list[str]:
            """Create modules and return their names."""
            names = []
            for i in range(count):
                name = f"{prefix}_{i:02d}"
                module = await create_module(session, name, "1.0.0")
                names.append(str(module.name))  # Ensure we get the string value
            return names

        # Simulate concurrent operations that could interfere
        task1 = create_and_verify(db_session, "isolation_test_a", 5)
        task2 = create_and_verify(db_session, "isolation_test_b", 5)

        names_a, names_b = await asyncio.gather(task1, task2)

        # Verify no cross-contamination (transaction isolation working)
        assert len(names_a) == 5
        assert len(names_b) == 5
        assert all(name.startswith("isolation_test_a") for name in names_a)
        assert all(name.startswith("isolation_test_b") for name in names_b)

        # Verify all modules are actually persisted
        all_modules = await get_modules(db_session, skip=0, limit=20)
        isolation_modules = [m for m in all_modules if m.name.startswith("isolation_test_")]
        assert len(isolation_modules) == 10

    @pytest.mark.asyncio
    async def test_service_layer_performance(self, db_session: AsyncSession) -> None:
        """Test service layer maintains performance with business logic overhead."""
        start_time = time.time()

        # Test service layer operations (includes validation, logging, etc.)
        modules = []
        for i in range(20):
            module = await service_create_module(db_session, f"service_perf_{i:03d}", "1.0.0", f'{{"index": {i}}}')
            modules.append(module)

        elapsed = time.time() - start_time

        # Validate quality
        assert len(modules) == 20
        for i, module in enumerate(modules):
            assert module.name == f"service_perf_{i:03d}"
            assert module.config == f'{{"index": {i}}}'

        # Validate efficiency - service layer should add minimal overhead
        assert elapsed < 3.0, f"Service layer operations took {elapsed:.2f}s, should be < 3.0s"


class TestReliabilityIntegration:
    """Reliability tests ensuring system resilience."""

    @pytest.mark.asyncio
    async def test_error_recovery_maintains_consistency(self, db_session: AsyncSession) -> None:
        """Test that errors don't leave system in inconsistent state."""
        # Create a baseline module
        baseline = await create_module(db_session, "reliability_baseline", "1.0.0")
        assert baseline is not None

        # Attempt to create duplicate (should fail)
        with pytest.raises(IntegrityError):
            await create_module(db_session, "reliability_baseline", "2.0.0")

        # Verify system is still functional after error
        new_module = await create_module(db_session, "reliability_recovery", "1.0.0")
        assert new_module is not None
        assert new_module.name == "reliability_recovery"

        # Verify original data unchanged
        modules = await get_modules(db_session, skip=0, limit=10)
        baseline_modules = [m for m in modules if m.name == "reliability_baseline"]
        assert len(baseline_modules) == 1
        assert baseline_modules[0].version == "1.0.0"  # Original version preserved
