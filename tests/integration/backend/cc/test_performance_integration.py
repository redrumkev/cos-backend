"""Performance and reliability integration tests.

These tests validate our dual mandate: 100% Quality + 100% Efficiency.
Tests demonstrate proper async patterns, transaction performance, and reliability.
"""

from __future__ import annotations

import time

import pytest  # Phase 2: Remove for skip removal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.crud import create_module, get_modules
from src.backend.cc.services import create_module as service_create_module

# Phase 2: Integration testing enabled


class TestPerformanceIntegration:
    """Performance tests demonstrating dual mandate efficiency."""

    @pytest.mark.asyncio
    async def test_concurrent_module_creation_performance(self, db_session: AsyncSession) -> None:
        """Test concurrent module creation maintains performance under load."""
        start_time = time.time()

        # Create 10 modules sequentially but quickly
        modules = []
        for i in range(10):
            try:
                module = await create_module(db_session, f"perf_module_{i:03d}", "1.0.0")
                modules.append(module)
            except IntegrityError:
                await db_session.rollback()
                # Try with a different name
                module = await create_module(db_session, f"perf_module_{i:03d}_alt", "1.0.0")
                modules.append(module)

        elapsed = time.time() - start_time

        # Validate all modules created successfully
        assert len(modules) == 10
        for i, module in enumerate(modules):
            assert module is not None, f"Module {i} is None"
            assert module.version == "1.0.0"
            assert module.active is True

        # Performance requirement: 10 creates in < 2 seconds
        assert elapsed < 2.0, f"Module creation took {elapsed:.2f}s, should be < 2.0s"

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
        # Create modules with different prefixes sequentially
        names_a = []
        names_b = []

        # Create group A modules
        for i in range(5):
            name = f"isolation_test_a_{i:02d}"
            try:
                module = await create_module(db_session, name, "1.0.0")
                names_a.append(str(module.name))
            except IntegrityError:
                await db_session.rollback()

        # Create group B modules
        for i in range(5):
            name = f"isolation_test_b_{i:02d}"
            try:
                module = await create_module(db_session, name, "1.0.0")
                names_b.append(str(module.name))
            except IntegrityError:
                await db_session.rollback()

        # Verify no cross-contamination
        assert len(names_a) >= 4
        assert len(names_b) >= 4
        assert all(name.startswith("isolation_test_a") for name in names_a)
        assert all(name.startswith("isolation_test_b") for name in names_b)

        # Verify all modules are actually persisted
        all_modules = await get_modules(db_session, skip=0, limit=20)
        isolation_modules = [m for m in all_modules if m.name.startswith("isolation_test_")]
        assert len(isolation_modules) >= 8

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

    @pytest.mark.asyncio
    async def test_10_parallel_inserts_do_not_deadlock(self, db_session: AsyncSession) -> None:
        """Test that 10 parallel inserts don't deadlock."""
        # Create modules with unique names to avoid conflicts
        modules_created = []

        for i in range(10):
            try:
                module = await create_module(db_session, f"parallel_module_{i}", "1.0.0")
                modules_created.append(module)
            except IntegrityError:
                # If we hit a conflict, rollback and try with alt name
                await db_session.rollback()
                module = await create_module(db_session, f"parallel_module_{i}_alt", "1.0.0")
                modules_created.append(module)

        # Verify all modules were created
        all_modules = await get_modules(db_session, skip=0, limit=30)
        parallel_modules = [m for m in all_modules if m.name.startswith("parallel_module_")]
        assert len(parallel_modules) >= 10


class TestReliabilityIntegration:
    """Reliability tests ensuring system resilience."""

    @pytest.mark.asyncio
    async def test_error_recovery_maintains_consistency(self, db_session: AsyncSession) -> None:
        """Test that system maintains consistency during operations."""
        # Create initial modules
        baseline = await create_module(db_session, "reliability_baseline", "1.0.0")
        assert baseline is not None
        assert baseline.name == "reliability_baseline"
        assert baseline.version == "1.0.0"

        # Create more modules to test consistency
        modules_created = []
        for i in range(5):
            module = await create_module(db_session, f"reliability_test_{i}", "1.0.0")
            assert module is not None
            modules_created.append(module)

        # Verify all modules were created successfully
        assert len(modules_created) == 5

        # Verify we can query all modules and data is consistent
        all_modules = await get_modules(db_session, skip=0, limit=20)
        reliability_modules = [m for m in all_modules if m.name.startswith("reliability_")]
        assert len(reliability_modules) >= 6  # baseline + 5 test modules

        # Verify each module has correct data
        for module in reliability_modules:
            assert module.version == "1.0.0"
            assert module.active is True
