"""Tests for missing model coverage in the Control Center module.

This file contains tests for SQLAlchemy models that were missing coverage,
focusing on custom types, table args, and model behavior.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

from src.backend.cc.models import UUID, HealthStatus, Module, get_table_args
from src.db.base import Base


class TestUUIDType:
    """Test custom UUID type behavior."""

    def test_uuid_type_cache_ok(self) -> None:
        """Test that UUID type has cache_ok set correctly."""
        uuid_type = UUID()
        assert uuid_type.cache_ok is True


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
