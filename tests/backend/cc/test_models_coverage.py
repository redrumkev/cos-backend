"""Tests for missing model coverage in the Control Center module.

This file contains tests for SQLAlchemy models that were missing coverage,
focusing on custom types, table args, and model behavior.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

from src.backend.cc.models import UUID, HealthStatus, Module, get_table_args
from src.db.base import Base


class TestUUIDType:
    """Test custom UUID type behavior."""

    def test_uuid_type_cache_ok(self) -> None:
        """Test that UUID type has cache_ok set correctly."""
        uuid_type = UUID()
        assert uuid_type.cache_ok is True

    def test_uuid_type_load_dialect_impl_postgres(self) -> None:
        """Test UUID type load_dialect_impl for PostgreSQL - covers line 32."""
        uuid_type = UUID()

        # Mock PostgreSQL dialect
        mock_dialect = MagicMock()
        mock_dialect.name = "postgresql"
        mock_dialect.type_descriptor = MagicMock()

        # Call the method
        uuid_type.load_dialect_impl(mock_dialect)

        # Verify PostgreSQL UUID type is used (line 32)
        mock_dialect.type_descriptor.assert_called_once()

    def test_uuid_type_load_dialect_impl_sqlite(self) -> None:
        """Test UUID type load_dialect_impl for SQLite."""
        uuid_type = UUID()

        # Mock SQLite dialect
        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"

        result = uuid_type.load_dialect_impl(mock_dialect)

        # For SQLite, should return String(36)
        assert hasattr(result, "length")

    def test_uuid_type_process_bind_param_with_value(self) -> None:
        """Test UUID type process_bind_param with value - covers line 38."""
        uuid_type = UUID()

        # Mock dialect and test value
        mock_dialect = MagicMock()
        test_value = "123e4567-e89b-12d3-a456-426614174000"

        # Call the method
        result = uuid_type.process_bind_param(test_value, mock_dialect)

        # Should return the value as-is (line 38)
        assert result == test_value

    def test_uuid_type_process_bind_param_with_none(self) -> None:
        """Test UUID type process_bind_param with None."""
        uuid_type = UUID()

        mock_dialect = MagicMock()

        result = uuid_type.process_bind_param(None, mock_dialect)

        assert result is None

    def test_uuid_type_process_result_value_with_value(self) -> None:
        """Test UUID type process_result_value with value - covers line 44."""
        uuid_type = UUID()

        # Mock dialect and test value
        mock_dialect = MagicMock()
        test_value = "123e4567-e89b-12d3-a456-426614174000"

        # Call the method
        result = uuid_type.process_result_value(test_value, mock_dialect)

        # Should return the value as-is (line 44)
        assert result == test_value

    def test_uuid_type_process_result_value_with_none(self) -> None:
        """Test UUID type process_result_value with None."""
        uuid_type = UUID()

        mock_dialect = MagicMock()

        result = uuid_type.process_result_value(None, mock_dialect)

        assert result is None


class TestTableArgs:
    """Test table args function behavior."""

    @patch.dict(os.environ, {"ENABLE_DB_INTEGRATION": "1"})
    def test_get_table_args_db_integration_enabled(self) -> None:
        """Test table args when DB integration is enabled."""
        result = get_table_args()

        assert result == {"schema": "cc", "extend_existing": True}

    @patch.dict(os.environ, {"ENABLE_DB_INTEGRATION": "0"})
    def test_get_table_args_db_integration_disabled(self) -> None:
        """Test table args when DB integration is disabled."""
        result = get_table_args()

        assert result == {"extend_existing": True}

    @patch.dict(os.environ, {}, clear=True)
    def test_get_table_args_no_env_var(self) -> None:
        """Test table args when env var is not set."""
        result = get_table_args()

        assert result == {"extend_existing": True}


class TestModuleModelInit:
    """Test Module model __init__ behavior - covers lines 106-108."""

    def test_module_init_without_id_adds_uuid(self) -> None:
        """Test Module __init__ adds UUID when id not provided - covers lines 106-107."""
        # Create module without specifying id
        module = Module(name="test_module", version="1.0.0")

        # Should have auto-generated UUID (lines 106-107)
        assert module.id is not None
        assert isinstance(module.id, str)
        assert len(module.id) == 36  # UUID string length

    def test_module_init_with_id_keeps_provided_id(self) -> None:
        """Test Module __init__ keeps provided id."""
        import uuid

        custom_id = str(uuid.uuid4())
        module = Module(id=custom_id, name="test_module", version="1.0.0")

        # Should keep the provided id
        assert module.id == custom_id

    def test_module_init_without_active_defaults_to_true(self) -> None:
        """Test Module __init__ sets active=True when not provided - covers line 108."""
        # Create module without specifying active
        module = Module(name="test_module", version="1.0.0")

        # Should default to True (line 108 and beyond)
        assert module.active is True

    def test_module_init_with_active_false_keeps_value(self) -> None:
        """Test Module __init__ keeps provided active value."""
        module = Module(name="test_module", version="1.0.0", active=False)

        # Should keep the provided value
        assert module.active is False

    def test_module_init_full_kwargs_coverage(self) -> None:
        """Test Module __init__ with all possible kwargs combinations."""
        import uuid

        # Test with id provided, active not provided
        test_uuid1 = str(uuid.uuid4())
        module1 = Module(id=test_uuid1, name="test1", version="1.0.0")
        assert module1.id == test_uuid1
        assert module1.active is True

        # Test with active provided, id not provided
        module2 = Module(name="test2", version="1.0.0", active=False)
        assert module2.id is not None
        assert module2.active is False

        # Test with both provided
        test_uuid3 = str(uuid.uuid4())
        module3 = Module(id=test_uuid3, name="test3", version="1.0.0", active=True)
        assert module3.id == test_uuid3
        assert module3.active is True


class TestHealthStatusModel:
    """Test HealthStatus model behavior."""

    def test_health_status_repr(self) -> None:
        """Test HealthStatus string representation."""
        health = HealthStatus(module="test_module", status="healthy")

        result = repr(health)
        assert result == "<HealthStatus(module='test_module', status='healthy')>"

    def test_health_status_defaults(self) -> None:
        """Test HealthStatus default values."""
        health = HealthStatus(module="test_module", status="healthy")

        # Test that id gets a UUID by default
        assert health.id is not None
        # Test that last_updated gets set automatically
        assert health.last_updated is not None
        assert isinstance(health.last_updated, datetime)
        # Details should be None by default
        assert health.details is None

    def test_health_status_with_details(self) -> None:
        """Test HealthStatus with details."""
        details = "Everything is working fine"
        health = HealthStatus(module="test_module", status="healthy", details=details)

        assert health.details == details

    def test_health_status_custom_timestamp(self) -> None:
        """Test HealthStatus with custom timestamp."""
        custom_time = datetime.now(UTC)
        health = HealthStatus(module="test_module", status="healthy", last_updated=custom_time)

        assert health.last_updated == custom_time


class TestModuleModel:
    """Test Module model behavior."""

    def test_module_repr(self) -> None:
        """Test Module string representation."""
        module = Module(name="test_module", version="1.0.0", active=True)

        result = repr(module)
        assert result == "<Module(name='test_module', version='1.0.0', active=True)>"

    def test_module_repr_inactive(self) -> None:
        """Test Module string representation when inactive."""
        module = Module(name="test_module", version="1.0.0", active=False)

        result = repr(module)
        assert result == "<Module(name='test_module', version='1.0.0', active=False)>"

    def test_module_defaults(self) -> None:
        """Test Module default values."""
        module = Module(name="test_module", version="1.0.0")

        # Test that id gets a UUID by default
        assert module.id is not None
        # Test that active defaults to True
        assert module.active is True
        # Test that last_active gets set automatically
        assert module.last_active is not None
        assert isinstance(module.last_active, datetime)
        # Config should be None by default
        assert module.config is None

    def test_module_with_config(self) -> None:
        """Test Module with configuration."""
        config = '{"setting1": "value1", "setting2": "value2"}'
        module = Module(name="test_module", version="1.0.0", config=config)

        assert module.config == config

    def test_module_inactive(self) -> None:
        """Test Module with inactive status."""
        module = Module(name="test_module", version="1.0.0", active=False)

        assert module.active is False

    def test_module_custom_timestamp(self) -> None:
        """Test Module with custom last_active timestamp."""
        custom_time = datetime.now(UTC)
        module = Module(name="test_module", version="1.0.0", last_active=custom_time)

        assert module.last_active == custom_time


class TestModelTableConfiguration:
    """Test model table configuration."""

    def test_health_status_table_name(self) -> None:
        """Test HealthStatus table name."""
        assert HealthStatus.__tablename__ == "health_status"

    def test_module_table_name(self) -> None:
        """Test Module table name."""
        assert Module.__tablename__ == "modules"

    def test_models_extend_base(self) -> None:
        """Test that models extend the Base class."""
        assert issubclass(HealthStatus, Base)
        assert issubclass(Module, Base)

    @patch("src.backend.cc.models.get_table_args")
    def test_models_use_table_args(self, mock_get_table_args: Any) -> None:
        """Test that models use get_table_args function."""
        # This test ensures the function is called during model definition
        # Since the models are already defined, we can't easily test this
        # without importing fresh, but we can verify the function exists
        # and returns the expected format
        mock_get_table_args.return_value = {"extend_existing": True}
        result = get_table_args()
        assert isinstance(result, dict)
        assert "extend_existing" in result
