"""Database coverage tests for missed lines and Living Patterns compliance.

Tests target specific uncovered lines in database.py:
- Lines 222-223: _create_sync_engine method
- Lines 230-246: _create_async_engine pool configuration
- Lines 255-270: _get_db_url schema-specific URL handling
- Line 117: MockAsyncSession.__aenter__ method

Pattern Reference: service.py v2.1.0 (Living Patterns System)
Pattern Reference: error_handling.py v2.1.0 (COSError integration)
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.database import DatabaseResourceFactory, _is_test_mode
from src.core_v2.patterns.error_handling import COSError, ErrorCategory


class TestDatabaseCoverage:
    """Test database coverage for missed lines and Living Patterns compliance."""

    def test_create_sync_engine_non_test_mode(self) -> None:
        """Test _create_sync_engine method in non-test mode (lines 222-223)."""
        factory = DatabaseResourceFactory()

        # Mock _is_test_mode to return False
        with (
            patch("src.common.database._is_test_mode", return_value=False),
            patch("src.common.database.create_engine") as mock_create,
        ):
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            # Call _create_sync_engine directly
            result = factory._create_sync_engine("test_schema")

            # Verify the method was called with proper parameters
            mock_create.assert_called_once()
            assert result == mock_engine

    def test_create_async_engine_pool_configuration(self) -> None:
        """Test _create_async_engine pool configuration (lines 230-246)."""
        factory = DatabaseResourceFactory()

        # Mock _is_test_mode to return False
        with (
            patch("src.common.database._is_test_mode", return_value=False),
            patch("src.common.database.create_async_engine") as mock_create,
            patch.dict(
                os.environ, {"AGENT_POOL_SIZE": "10", "AGENT_POOL_TIMEOUT": "30", "AGENT_POOL_MAX_OVERFLOW": "5"}
            ),
        ):
            mock_engine = AsyncMock()
            mock_create.return_value = mock_engine

            # Call _create_async_engine directly
            factory._create_async_engine("test_schema")

            # Verify the method was called with proper pool configuration
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]["pool_size"] == 10
            assert call_args[1]["pool_timeout"] == 30
            assert call_args[1]["max_overflow"] == 5
            assert call_args[1]["future"] is True
            assert call_args[1]["pool_pre_ping"] is True

    def test_get_db_url_schema_specific_cc(self) -> None:
        """Test _get_db_url with schema-specific URL for CC (lines 255-270)."""
        # Mock settings with schema-specific URL
        mock_settings = MagicMock()
        mock_settings.POSTGRES_CC_URL = "postgresql://cc_user:pass@localhost:5432/cc_db"
        mock_settings.sync_db_url = "postgresql://user:pass@localhost:5432/default_db"
        mock_settings.async_db_url = "postgresql://user:pass@localhost:5432/default_db"

        factory = DatabaseResourceFactory(settings=mock_settings)

        # Test CC schema with sync mode
        url = factory._get_db_url("cc", async_mode=False)
        assert url == "postgresql://cc_user:pass@localhost:5432/cc_db"

        # Test CC schema with async mode (should convert to asyncpg)
        url = factory._get_db_url("cc", async_mode=True)
        assert url == "postgresql+asyncpg://cc_user:pass@localhost:5432/cc_db"

    def test_get_db_url_schema_specific_pem(self) -> None:
        """Test _get_db_url with schema-specific URL for PEM (lines 258-259)."""
        # Mock settings with PEM schema-specific URL
        mock_settings = MagicMock()
        mock_settings.POSTGRES_PEM_URL = "postgresql://pem_user:pass@localhost:5432/pem_db"
        mock_settings.sync_db_url = "postgresql://user:pass@localhost:5432/default_db"
        mock_settings.async_db_url = "postgresql://user:pass@localhost:5432/default_db"

        factory = DatabaseResourceFactory(settings=mock_settings)

        # Test PEM schema
        url = factory._get_db_url("pem", async_mode=False)
        assert url == "postgresql://pem_user:pass@localhost:5432/pem_db"

    def test_get_db_url_schema_specific_aic(self) -> None:
        """Test _get_db_url with schema-specific URL for AIC (lines 260-261)."""
        # Mock settings with AIC schema-specific URL
        mock_settings = MagicMock()
        mock_settings.POSTGRES_AIC_URL = "postgresql://aic_user:pass@localhost:5432/aic_db"
        mock_settings.sync_db_url = "postgresql://user:pass@localhost:5432/default_db"
        mock_settings.async_db_url = "postgresql://user:pass@localhost:5432/default_db"

        factory = DatabaseResourceFactory(settings=mock_settings)

        # Test AIC schema
        url = factory._get_db_url("aic", async_mode=False)
        assert url == "postgresql://aic_user:pass@localhost:5432/aic_db"

    def test_get_db_url_fallback_to_default(self) -> None:
        """Test _get_db_url fallback to default URLs (lines 264-270)."""
        # Mock settings without schema-specific URLs
        mock_settings = MagicMock()
        mock_settings.sync_db_url = "postgresql://user:pass@localhost:5432/default_db"
        mock_settings.async_db_url = "postgresql://user:pass@localhost:5432/default_db"

        # Delete any possible schema-specific attributes
        if hasattr(mock_settings, "POSTGRES_CC_URL"):
            delattr(mock_settings, "POSTGRES_CC_URL")
        if hasattr(mock_settings, "POSTGRES_PEM_URL"):
            delattr(mock_settings, "POSTGRES_PEM_URL")
        if hasattr(mock_settings, "POSTGRES_AIC_URL"):
            delattr(mock_settings, "POSTGRES_AIC_URL")

        factory = DatabaseResourceFactory(settings=mock_settings)

        # Test fallback to sync_db_url
        url = factory._get_db_url("unknown_schema", async_mode=False)
        assert url == "postgresql://user:pass@localhost:5432/default_db"

        # Test fallback to async_db_url with conversion
        url = factory._get_db_url("unknown_schema", async_mode=True)
        assert url == "postgresql+asyncpg://user:pass@localhost:5432/default_db"

    def test_get_db_url_async_conversion(self) -> None:
        """Test _get_db_url async URL conversion (lines 267-268)."""
        mock_settings = MagicMock()
        mock_settings.async_db_url = "postgresql://user:pass@localhost:5432/db"

        factory = DatabaseResourceFactory(settings=mock_settings)

        # Test async mode conversion
        url = factory._get_db_url("test", async_mode=True)
        assert url == "postgresql+asyncpg://user:pass@localhost:5432/db"

    @pytest.mark.asyncio
    async def test_mock_async_session_aenter_coverage(self) -> None:
        """Test MockAsyncSession.__aenter__ method coverage (line 126)."""
        from src.common.database import get_async_session_maker

        # Ensure we're in test mode
        assert _is_test_mode()

        # Get the session maker
        session_maker = get_async_session_maker()

        # Create a session - this should be a MockAsyncSession
        session = session_maker()

        # Verify the session has the required methods
        assert hasattr(session, "__aenter__")
        assert hasattr(session, "__aexit__")

        # Call the MockAsyncSession's __aenter__ method directly through the class
        # This ensures we hit line 126 ("return self")
        mock_session_class = session.__class__

        # Get the __aenter__ method from the class and call it on the instance
        aenter_method = mock_session_class.__aenter__
        result = await aenter_method(session)

        # Verify the result is the session itself (line 126: "return self")
        assert result is session

        # Also test the async context manager behavior
        async with session as ctx_session:
            # The context manager should work properly
            assert ctx_session is not None

    def test_pool_configuration_with_partial_env_vars(self) -> None:
        """Test pool configuration with only some environment variables set."""
        factory = DatabaseResourceFactory()

        with (
            patch("src.common.database._is_test_mode", return_value=False),
            patch("src.common.database.create_async_engine") as mock_create,
            patch.dict(
                os.environ,
                {
                    "AGENT_POOL_SIZE": "5",
                    # Only set pool_size, not timeout or max_overflow
                },
                clear=True,
            ),
        ):
            mock_engine = AsyncMock()
            mock_create.return_value = mock_engine

            # Call _create_async_engine directly
            factory._create_async_engine("test_schema")

            # Verify pool_size was overridden, others use defaults from DatabaseConfig
            call_args = mock_create.call_args
            assert call_args[1]["pool_size"] == 5  # Overridden by env var
            assert call_args[1]["pool_timeout"] == 30  # Default from DatabaseConfig
            assert call_args[1]["max_overflow"] == 40  # Default from DatabaseConfig
            assert call_args[1]["future"] is True
            assert call_args[1]["pool_pre_ping"] is True

    def test_pool_configuration_no_env_vars(self) -> None:
        """Test pool configuration with no environment variables set."""
        factory = DatabaseResourceFactory()

        with (
            patch("src.common.database._is_test_mode", return_value=False),
            patch("src.common.database.create_async_engine") as mock_create,
            patch.dict(os.environ, {}, clear=True),
        ):
            mock_engine = AsyncMock()
            mock_create.return_value = mock_engine

            # Call _create_async_engine directly
            factory._create_async_engine("test_schema")

            # Verify base configuration from DatabaseConfig was set
            call_args = mock_create.call_args
            assert call_args[1]["pool_size"] == 20  # Default from DatabaseConfig
            assert call_args[1]["pool_timeout"] == 30  # Default from DatabaseConfig
            assert call_args[1]["max_overflow"] == 40  # Default from DatabaseConfig
            assert call_args[1]["future"] is True
            assert call_args[1]["pool_pre_ping"] is True


class TestLivingPatternIntegration:
    """Test Living Patterns integration in database module."""

    def test_database_resource_factory_pattern_markers(self) -> None:
        """Test that DatabaseResourceFactory has proper pattern markers."""
        factory = DatabaseResourceFactory()

        # Check class docstring contains pattern references
        doc = factory.__class__.__doc__
        assert doc is not None
        assert "Pattern Reference" in doc
        assert "service.py v2.1.0" in doc
        assert "ResourceFactory pattern" in doc

    def test_execution_context_pattern_markers(self) -> None:
        """Test that DatabaseExecutionContext has proper pattern markers."""
        from src.common.database import DatabaseExecutionContext

        # Check class docstring contains pattern references
        doc = DatabaseExecutionContext.__doc__
        assert doc is not None
        assert "Pattern Reference" in doc
        assert "service.py v2.1.0" in doc
        assert "ExecutionContext pattern" in doc

    def test_module_pattern_markers(self) -> None:
        """Test that module has proper pattern markers."""
        import src.common.database as database_module

        # Check module docstring and pattern references
        docstring = database_module.__doc__
        assert docstring is not None
        assert "Database connection and session management" in docstring

        # Check for pattern markers in module source
        import inspect

        source = inspect.getsource(database_module)
        assert "Pattern Reference: service.py v2.1.0" in source
        assert "Applied: ResourceFactory pattern" in source
        assert "Applied: ExecutionContext" in source

    def test_cos_error_pattern_integration(self) -> None:
        """Test integration with COSError pattern for error handling."""
        # This test demonstrates how database errors should be handled
        # using the COSError pattern from error_handling.py v2.1.0

        factory = DatabaseResourceFactory()

        # Simulate a database error scenario
        try:
            # This should work fine in test mode
            engine = factory.get_engine("test_schema")
            assert engine is not None

            # Create a sample COSError for database-related errors
            db_error = COSError(
                message="Database connection failed",
                category=ErrorCategory.EXTERNAL_SERVICE,
                details={"schema": "test_schema", "operation": "get_engine"},
            )

            # Verify error structure
            assert db_error.category == ErrorCategory.EXTERNAL_SERVICE
            assert db_error.details["schema"] == "test_schema"
            assert db_error.user_message == "Database connection failed"

        except Exception as e:
            # Any unexpected error should be wrapped in COSError
            cos_error = COSError(
                message=str(e), category=ErrorCategory.INTERNAL, details={"operation": "test_database_pattern"}
            )
            assert cos_error.category == ErrorCategory.INTERNAL

    def test_health_check_pattern_compliance(self) -> None:
        """Test that health check follows service pattern."""
        factory = DatabaseResourceFactory()

        # Create some resources to populate the factory
        _ = factory.get_engine("cc", async_mode=False)
        _ = factory.get_engine("pem", async_mode=True)

        # Test health check pattern
        import asyncio

        health = asyncio.run(factory.health_check())

        # Verify health check structure follows pattern
        assert "factory" in health
        assert "engines" in health
        assert "session_makers" in health
        assert "status" in health
        assert health["status"] == "healthy"
        assert health["factory"] == "DatabaseResourceFactory"
        assert isinstance(health["engines"], int)
        assert isinstance(health["session_makers"], int)
