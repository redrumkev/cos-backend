"""Focused tests for schemas.py edge cases and missing coverage.

This file targets specific missing lines in schemas.py to achieve 100% coverage.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.backend.cc.schemas import (
    CCConfig,
    HealthStatus,
    HealthStatusResponse,
    Module,
    ModuleBase,
    ModulePingRequest,
    ModulePingResponse,
    ModuleUpdate,
)


class TestFieldSerializers:
    """Test field serializers in schemas - covers missing serialization lines."""

    def test_health_status_response_serialize_last_updated(self):
        """Test HealthStatusResponse serialize_last_updated method - covers line 37."""
        # Create a datetime object
        test_datetime = datetime(2025, 1, 1, 12, 0, 0)

        # Create HealthStatusResponse instance
        health_status = HealthStatusResponse(
            id="test-id", module="cc", status="healthy", last_updated=test_datetime, details="Test details"
        )

        # Convert to dict (triggers serialization)
        data = health_status.model_dump()

        # Verify the datetime was serialized to ISO string
        assert data["last_updated"] == "2025-01-01T12:00:00"

        # Also test the serialization method directly
        serialized = health_status.serialize_last_updated(test_datetime)
        assert serialized == "2025-01-01T12:00:00"

    def test_module_serialize_last_active(self):
        """Test Module serialize_last_active method."""
        # Create a datetime object
        test_datetime = datetime(2025, 1, 1, 12, 0, 0)

        # Create Module instance
        module = Module(
            id="test-id",
            name="test_module",
            version="1.0.0",
            active=True,
            last_active=test_datetime,
            config='{"test": "value"}',
        )

        # Convert to dict (triggers serialization)
        data = module.model_dump()

        # Verify the datetime was serialized to ISO string
        assert data["last_active"] == "2025-01-01T12:00:00"

        # Also test the serialization method directly
        serialized = module.serialize_last_active(test_datetime)
        assert serialized == "2025-01-01T12:00:00"


class TestSchemaValidation:
    """Test schema validation edge cases."""

    def test_module_ping_request_empty_module_validation(self):
        """Test ModulePingRequest validates minimum length."""
        with pytest.raises(ValidationError) as exc_info:
            ModulePingRequest(module="")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "at least 1 character" in str(errors[0])

    def test_module_base_validation_edge_cases(self):
        """Test ModuleBase field validations."""
        # Test minimum length validation for name
        with pytest.raises(ValidationError):
            ModuleBase(name="", version="1.0.0")

        # Test minimum length validation for version
        with pytest.raises(ValidationError):
            ModuleBase(name="test", version="")

        # Test maximum length validation for name (255 chars)
        long_name = "a" * 256
        with pytest.raises(ValidationError):
            ModuleBase(name=long_name, version="1.0.0")

        # Test maximum length validation for version (50 chars)
        long_version = "1." + "0" * 49
        with pytest.raises(ValidationError):
            ModuleBase(name="test", version=long_version)

    def test_module_update_optional_fields(self):
        """Test ModuleUpdate with all None values."""
        # This should be valid since all fields are optional
        update = ModuleUpdate()
        assert update.name is None
        assert update.version is None
        assert update.active is None
        assert update.config is None

        # Test with some values
        update = ModuleUpdate(name="test", active=False)
        assert update.name == "test"
        assert update.version is None
        assert update.active is False
        assert update.config is None


class TestSchemaDefaults:
    """Test schema default values."""

    def test_health_status_default(self):
        """Test HealthStatus default value."""
        health = HealthStatus()
        assert health.status == "healthy"

    def test_cc_config_defaults(self):
        """Test CCConfig default values."""
        config = CCConfig()
        assert config.version == "0.1.0"
        assert config.modules_loaded == ["cc"]


class TestSchemaExamples:
    """Test that schema examples are valid."""

    def test_health_status_example(self):
        """Test HealthStatus example data."""
        example_data = {"status": "healthy"}
        health = HealthStatus(**example_data)
        assert health.status == "healthy"

    def test_health_status_response_example(self):
        """Test HealthStatusResponse example data."""
        example_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "module": "cc",
            "status": "healthy",
            "last_updated": datetime.fromisoformat("2025-04-02T10:00:00"),
            "details": "All systems operational",
        }
        health = HealthStatusResponse(**example_data)
        assert health.id == "123e4567-e89b-12d3-a456-426614174000"
        assert health.module == "cc"

    def test_module_ping_request_example(self):
        """Test ModulePingRequest example data."""
        example_data = {"module": "mem0"}
        ping = ModulePingRequest(**example_data)
        assert ping.module == "mem0"

    def test_module_ping_response_example(self):
        """Test ModulePingResponse example data."""
        example_data = {"module": "mem0", "status": "healthy", "latency_ms": 5}
        response = ModulePingResponse(**example_data)
        assert response.module == "mem0"
        assert response.status == "healthy"
        assert response.latency_ms == 5


class TestSchemaConfigDict:
    """Test schema configuration dictionaries."""

    def test_health_status_response_from_attributes(self):
        """Test HealthStatusResponse can be created from SQLAlchemy model attributes."""

        # Mock an SQLAlchemy model object
        class MockModel:
            id = "test-id"
            module = "cc"
            status = "healthy"
            last_updated = datetime(2025, 1, 1, 12, 0, 0)
            details = "Test details"

        mock_model = MockModel()

        # Test from_attributes=True allows creation from model
        health = HealthStatusResponse.model_validate(mock_model)
        assert health.id == "test-id"
        assert health.module == "cc"
        assert health.status == "healthy"

    def test_module_from_attributes(self):
        """Test Module can be created from SQLAlchemy model attributes."""

        # Mock an SQLAlchemy model object
        class MockModel:
            id = "test-id"
            name = "test_module"
            version = "1.0.0"
            active = True
            last_active = datetime(2025, 1, 1, 12, 0, 0)
            config = '{"test": "value"}'

        mock_model = MockModel()

        # Test from_attributes=True allows creation from model
        module = Module.model_validate(mock_model)
        assert module.id == "test-id"
        assert module.name == "test_module"
        assert module.version == "1.0.0"
        assert module.active is True
