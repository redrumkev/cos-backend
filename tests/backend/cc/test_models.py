"""Tests for the SQLAlchemy models in the CC module.

This file contains tests for the database models defined in models.py,
verifying their structure, properties, and behaviors.
"""

# MDC: cc_module
from datetime import UTC, datetime

from sqlalchemy import inspect

from src.backend.cc.models import Base, HealthStatus, Module


class TestHealthStatusModel:
    """Tests for the HealthStatus model."""

    def test_table_name_and_schema(self) -> None:
        """Test that the table name and schema are correctly defined."""
        assert HealthStatus.__tablename__ == "health_status"
        assert HealthStatus.__table_args__ == {"schema": "cc"}

    def test_columns_exist(self) -> None:
        """Test that all expected columns exist in the model."""
        columns = inspect(HealthStatus).columns
        column_names = columns.keys()

        assert "id" in column_names
        assert "module" in column_names
        assert "status" in column_names
        assert "last_updated" in column_names
        assert "details" in column_names

    def test_column_types(self) -> None:
        """Test that column types are correctly defined."""
        columns = inspect(HealthStatus).columns

        # Check types and constraints
        assert str(columns["id"].type) == "UUID"
        assert columns["id"].primary_key is True

        assert str(columns["module"].type) == "VARCHAR"
        assert columns["module"].nullable is False
        assert columns["module"].unique is True
        assert columns["module"].index is True

        assert str(columns["status"].type) == "VARCHAR"
        assert columns["status"].nullable is False

        assert str(columns["last_updated"].type) == "DATETIME"
        assert columns["last_updated"].nullable is False

        assert str(columns["details"].type) == "VARCHAR"
        assert columns["details"].nullable is True

    def test_instance_creation(self) -> None:
        """Test creation of a HealthStatus instance."""
        # Create instance with manually set values (since in-memory tests
        # don't trigger default value generators)
        now = datetime.now(UTC)
        health_status = HealthStatus(
            module="test_module",
            status="healthy",
            details="All systems operational",
            last_updated=now,
        )

        # Verify attributes
        assert health_status.module == "test_module"
        assert health_status.status == "healthy"
        assert health_status.details == "All systems operational"
        assert health_status.last_updated == now

    def test_repr(self) -> None:
        """Test the string representation of a HealthStatus instance."""
        # Test with minimal required attributes
        health_status = HealthStatus(module="test_module", status="healthy")
        expected = "<HealthStatus(module='test_module', status='healthy')>"
        assert repr(health_status) == expected

        # Test with different values
        health_status = HealthStatus(module="different_module", status="degraded")
        expected = "<HealthStatus(module='different_module', status='degraded')>"
        assert repr(health_status) == expected

    def test_default_field_definitions(self) -> None:
        """Test that default values are defined correctly in the model."""
        # Instead of checking instance defaults (which require DB session),
        # check that the column definitions include defaults where expected
        columns = inspect(HealthStatus).columns

        # Check that last_updated has a default value defined
        assert columns["last_updated"].default is not None

        # Check that id has a default function (uuid4)
        assert columns["id"].default is not None

        # Check nullable fields
        assert columns["details"].nullable is True


class TestModuleModel:
    """Tests for the Module model."""

    def test_table_name_and_schema(self) -> None:
        """Test that the table name and schema are correctly defined."""
        assert Module.__tablename__ == "modules"
        assert Module.__table_args__ == {"schema": "cc"}

    def test_columns_exist(self) -> None:
        """Test that all expected columns exist in the model."""
        columns = inspect(Module).columns
        column_names = columns.keys()

        assert "id" in column_names
        assert "name" in column_names
        assert "version" in column_names
        assert "active" in column_names
        assert "last_active" in column_names
        assert "config" in column_names

    def test_column_types(self) -> None:
        """Test that column types are correctly defined."""
        columns = inspect(Module).columns

        # Check types and constraints
        assert str(columns["id"].type) == "UUID"
        assert columns["id"].primary_key is True

        assert str(columns["name"].type) == "VARCHAR"
        assert columns["name"].nullable is False
        assert columns["name"].unique is True
        assert columns["name"].index is True

        assert str(columns["version"].type) == "VARCHAR"
        assert columns["version"].nullable is False

        assert str(columns["active"].type) == "VARCHAR"
        assert columns["active"].nullable is False

        assert str(columns["last_active"].type) == "DATETIME"
        assert columns["last_active"].nullable is False

        assert str(columns["config"].type) == "VARCHAR"
        assert columns["config"].nullable is True

    def test_instance_creation(self) -> None:
        """Test creation of a Module instance."""
        # Create instance with manually set values (since in-memory tests
        # don't trigger default value generators)
        now = datetime.now(UTC)
        module = Module(
            name="test_module",
            version="1.0.0",
            active=True,
            config='{"setting": "value"}',
            last_active=now,
        )

        # Verify attributes
        assert module.name == "test_module"
        assert module.version == "1.0.0"
        assert module.active is True
        assert module.config == '{"setting": "value"}'
        assert module.last_active == now

    def test_repr(self) -> None:
        """Test the string representation of a Module instance."""
        # Test with typical values
        module = Module(name="test_module", version="1.0.0", active=True)
        expected = "<Module(name='test_module', version='1.0.0', active=True)>"
        assert repr(module) == expected

        # Test with different values
        module = Module(name="different_module", version="2.0.0", active=False)
        expected = "<Module(name='different_module', version='2.0.0', active=False)>"
        assert repr(module) == expected

    def test_default_field_definitions(self) -> None:
        """Test that default values are defined correctly in the model."""
        # Instead of checking instance defaults (which require DB session),
        # check that the column definitions include defaults where expected
        columns = inspect(Module).columns

        # Check that last_active has a default value defined
        assert columns["last_active"].default is not None

        # Check that id has a default function (uuid4)
        assert columns["id"].default is not None

        # Check that active has a default
        assert columns["active"].default is not None

        # Check nullable fields
        assert columns["config"].nullable is True


class TestDeclarativeBase:
    """Tests for the base declarative model."""

    def test_base_type(self) -> None:
        """Test that the Base is a proper SQLAlchemy declarative base."""
        # Base is a SQLAlchemy declarative base
        assert hasattr(Base, "__table__") is False
        assert hasattr(Base, "__tablename__") is False
        assert hasattr(Base, "__abstract__") is True

    def test_health_status_inherits_base(self) -> None:
        """Test that HealthStatus inherits from Base."""
        assert issubclass(HealthStatus, Base)

    def test_module_inherits_base(self) -> None:
        """Test that Module inherits from Base."""
        assert issubclass(Module, Base)


class TestEdgeCases:
    """Tests for model edge cases."""

    def test_health_status_required_fields(self) -> None:
        """Test that required fields can be set on HealthStatus."""
        # Create instance with only required fields
        health = HealthStatus(module="test_module", status="healthy")

        # Verify required fields are set
        assert health.module == "test_module"
        assert health.status == "healthy"

        # Optional fields should be None
        assert health.details is None

    def test_module_required_fields(self) -> None:
        """Test that required fields can be set on Module."""
        # Create instance with only required fields
        module = Module(name="test_module", version="1.0.0")

        # Verify required fields are set
        assert module.name == "test_module"
        assert module.version == "1.0.0"

        # Optional fields should have defaults or be None
        assert module.config is None
