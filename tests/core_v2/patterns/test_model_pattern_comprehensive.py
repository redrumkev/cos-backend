"""Comprehensive tests for COS Pydantic Model Pattern.

Tests all aspects of the model pattern including:
- Base model hierarchy and configurations
- Field validation library
- Performance optimizations
- SQLAlchemy integration
- Custom field types
- Testing utilities
- Serialization patterns

Target: 98%+ coverage for model pattern validation.
"""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field, ValidationError, field_validator

from src.core_v2.patterns.model import (
    DATETIME_ADAPTER,
    EMAIL_ADAPTER,
    UUID_ADAPTER,
    UUID_LIST_ADAPTER,
    APIResponse,
    COSAPIModel,
    COSBaseModel,
    COSConfigModel,
    COSDBModel,
    COSEmailStr,
    COSModuleName,
    DescriptionField,
    EmailField,
    ErrorResponse,
    ModelTestBase,
    NameField,
    PaginationRequest,
    PerformanceOptimizedMixin,
    SQLAlchemyIntegrationMixin,
    TimestampField,
    UUIDField,
)


class TestCOSBaseModel:
    """Test the foundational COSBaseModel configuration and behavior."""

    def test_model_config_settings(self) -> None:
        """Test that COSBaseModel has optimal ConfigDict settings."""
        config = COSBaseModel.model_config

        # Performance optimizations
        assert config["str_strip_whitespace"] is True
        assert config["validate_assignment"] is True
        assert config["use_enum_values"] is True
        assert config["defer_build"] is False

        # Integration requirements
        assert config["from_attributes"] is True
        assert config["populate_by_name"] is True

        # Data integrity
        assert config["extra"] == "forbid"
        assert config["arbitrary_types_allowed"] is False

        # Serialization standards
        assert config["ser_json_timedelta"] == "iso8601"
        assert config["ser_json_bytes"] == "base64"

    def test_base_model_inheritance(self) -> None:
        """Test that models can inherit from COSBaseModel."""

        class TestModel(COSBaseModel):
            name: str
            value: int

        model = TestModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42

    def test_str_strip_whitespace(self) -> None:
        """Test automatic string whitespace stripping."""

        class TestModel(COSBaseModel):
            name: str

        model = TestModel(name="  test  ")
        assert model.name == "test"

    def test_validate_assignment(self) -> None:
        """Test that assignment validation works."""

        class TestModel(COSBaseModel):
            value: int

        model = TestModel(value=42)
        with pytest.raises(ValidationError):
            model.value = "invalid"  # type: ignore[assignment]

    def test_extra_forbid(self) -> None:
        """Test that extra fields are forbidden."""

        class TestModel(COSBaseModel):
            name: str

        with pytest.raises(ValidationError) as exc_info:
            TestModel(name="test", extra_field="should_fail")  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"


class TestSpecializedModels:
    """Test COSAPIModel, COSDBModel, and COSConfigModel specializations."""

    def test_cos_api_model(self) -> None:
        """Test COSAPIModel with API-specific features."""

        class APITestModel(COSAPIModel):
            name: str
            value: int

        model = APITestModel(name="test", value=42)
        assert model.__api_version__ == "v1"
        assert model.__api_category__ == "general"

        # Should inherit all COSBaseModel config
        config = APITestModel.model_config
        assert config["from_attributes"] is True
        assert config["str_strip_whitespace"] is True

    def test_cos_db_model(self) -> None:
        """Test COSDBModel with database-specific optimizations."""

        class DBTestModel(COSDBModel):
            id: UUID
            name: str

        test_id = uuid4()
        model = DBTestModel(id=test_id, name="test")
        assert model.id == test_id

        # Should have validate_default=True
        config = DBTestModel.model_config
        assert config["validate_default"] is True
        assert config["from_attributes"] is True

    def test_cos_config_model(self) -> None:
        """Test COSConfigModel for configuration management."""

        class ConfigTestModel(COSConfigModel):
            DEBUG: bool = False
            PORT: int = 8000

        model = ConfigTestModel(DEBUG=True, PORT=3000)  # Test case insensitive
        assert model.DEBUG is True
        assert model.PORT == 3000

        # Should ignore extra fields
        config = ConfigTestModel.model_config
        assert config["extra"] == "ignore"


class TestFieldValidationLibrary:
    """Test custom field types and validators."""

    def test_uuid_field(self) -> None:
        """Test UUIDField annotation."""

        class TestModel(COSBaseModel):
            id: UUIDField

        test_id = uuid4()
        model = TestModel(id=test_id)
        assert isinstance(model.id, UUID)
        assert model.id == test_id

        # Test string UUID conversion
        model2 = TestModel(id=str(test_id))
        assert model2.id == test_id

    def test_timestamp_field(self) -> None:
        """Test TimestampField annotation."""

        class TestModel(COSBaseModel):
            created_at: TimestampField

        now = datetime.now(UTC)
        model = TestModel(created_at=now)
        assert isinstance(model.created_at, datetime)
        assert model.created_at == now

    def test_email_field(self) -> None:
        """Test EmailField pattern validation."""

        class TestModel(COSBaseModel):
            email: EmailField

        # Valid email
        model = TestModel(email="test@example.com")
        assert model.email == "test@example.com"

        # Invalid email
        with pytest.raises(ValidationError):
            TestModel(email="invalid-email")

    def test_name_field(self) -> None:
        """Test NameField length validation."""

        class TestModel(COSBaseModel):
            name: NameField

        # Valid name
        model = TestModel(name="Valid Name")
        assert model.name == "Valid Name"

        # Empty name
        with pytest.raises(ValidationError):
            TestModel(name="")

        # Too long name
        with pytest.raises(ValidationError):
            TestModel(name="x" * 256)

    def test_description_field(self) -> None:
        """Test DescriptionField length validation."""

        class TestModel(COSBaseModel):
            description: DescriptionField

        # Valid description
        model = TestModel(description="Valid description")
        assert model.description == "Valid description"

        # Too long description
        with pytest.raises(ValidationError):
            TestModel(description="x" * 1001)


class TestPerformanceAdapters:
    """Test TypeAdapter performance optimizations."""

    def test_uuid_adapter(self) -> None:
        """Test UUID TypeAdapter functionality."""
        test_uuid = uuid4()

        # Validate UUID object
        result = UUID_ADAPTER.validate_python(test_uuid)
        assert result == test_uuid

        # Validate UUID string
        result = UUID_ADAPTER.validate_python(str(test_uuid))
        assert result == test_uuid

    def test_uuid_list_adapter(self) -> None:
        """Test UUID list TypeAdapter functionality."""
        test_uuids = [uuid4(), uuid4()]

        # Validate list of UUIDs
        result = UUID_LIST_ADAPTER.validate_python(test_uuids)
        assert result == test_uuids

        # Validate list of UUID strings
        uuid_strings = [str(u) for u in test_uuids]
        result = UUID_LIST_ADAPTER.validate_python(uuid_strings)
        assert result == test_uuids

    def test_datetime_adapter(self) -> None:
        """Test datetime TypeAdapter functionality."""
        now = datetime.now(UTC)

        # Validate datetime object
        result = DATETIME_ADAPTER.validate_python(now)
        assert result == now

        # Validate ISO string
        result = DATETIME_ADAPTER.validate_python(now.isoformat())
        assert result.replace(microsecond=0) == now.replace(microsecond=0)

    def test_email_adapter(self) -> None:
        """Test email TypeAdapter functionality."""
        email = "test@example.com"

        result = EMAIL_ADAPTER.validate_python(email)
        assert result == email


class TestSQLAlchemyIntegration:
    """Test SQLAlchemy integration patterns."""

    def test_sqlalchemy_integration_mixin(self) -> None:
        """Test SQLAlchemy conversion methods."""

        class TestModel(COSDBModel, SQLAlchemyIntegrationMixin):
            id: UUID
            name: str
            value: int

        # Mock SQLAlchemy object
        class MockSQLAlchemyObj:
            def __init__(self) -> None:
                self.id = uuid4()
                self.name = "test"
                self.value = 42

        db_obj = MockSQLAlchemyObj()

        # Test from_sqlalchemy conversion
        model = TestModel.from_sqlalchemy(db_obj)
        assert model.id == db_obj.id  # type: ignore[attr-defined]
        assert model.name == db_obj.name  # type: ignore[attr-defined]
        assert model.value == db_obj.value  # type: ignore[attr-defined]

        # Test to_sqlalchemy_dict conversion
        data = model.to_sqlalchemy_dict()  # type: ignore[attr-defined]
        expected_keys = {"id", "name", "value"}
        assert set(data.keys()) == expected_keys

    def test_from_sqlalchemy_list(self) -> None:
        """Test bulk SQLAlchemy object conversion."""

        class TestModel(COSDBModel, SQLAlchemyIntegrationMixin):
            id: UUID
            name: str

        # Mock SQLAlchemy objects
        class MockObj:
            def __init__(self, name: str) -> None:
                self.id = uuid4()
                self.name = name

        db_objects = [MockObj("test1"), MockObj("test2")]

        # Test bulk conversion
        models = TestModel.from_sqlalchemy_list(db_objects)
        assert len(models) == 2
        assert all(isinstance(m, TestModel) for m in models)
        assert models[0].name == "test1"  # type: ignore[attr-defined]
        assert models[1].name == "test2"  # type: ignore[attr-defined]


class TestPerformanceOptimizations:
    """Test performance optimization patterns."""

    def test_performance_optimized_mixin(self) -> None:
        """Test performance optimization methods."""

        class TestModel(COSBaseModel, PerformanceOptimizedMixin):
            name: str
            value: int
            optional: str | None = None

        model = TestModel(name="test", value=42)

        # Test high-performance JSON serialization
        json_bytes = model.to_json_bytes()
        assert isinstance(json_bytes, bytes)

        # Verify it's valid JSON
        data = json.loads(json_bytes.decode("utf-8"))
        assert data["name"] == "test"
        assert data["value"] == 42

        # Test memory-efficient serialization
        clean_dict = model.to_dict_exclude_none()
        assert "optional" not in clean_dict
        assert clean_dict["name"] == "test"

        # Test API response optimization
        api_dict = model.to_dict_api_response()
        assert "name" in api_dict
        assert "value" in api_dict


class TestCommonPatterns:
    """Test common request/response patterns."""

    def test_pagination_request(self) -> None:
        """Test pagination request validation and calculations."""
        # Default values
        pagination = PaginationRequest()
        assert pagination.page == 1
        assert pagination.limit == 20
        assert pagination.offset == 0

        # Custom values
        pagination = PaginationRequest(page=3, limit=50)
        assert pagination.page == 3
        assert pagination.limit == 50
        assert pagination.offset == 100  # (3-1) * 50

        # Test sqlalchemy_slice property
        slice_obj = pagination.sqlalchemy_slice
        assert slice_obj.start == 100
        assert slice_obj.stop == 150

        # Validation limits
        with pytest.raises(ValidationError):
            PaginationRequest(page=0)  # Below minimum

        with pytest.raises(ValidationError):
            PaginationRequest(limit=101)  # Above maximum

    def test_api_response(self) -> None:
        """Test generic API response wrapper."""
        # Success response
        response = APIResponse[str](data="test data")  # type: ignore[type-var]
        assert response.success is True
        assert response.data == "test data"
        assert response.error is None
        assert isinstance(response.timestamp, datetime)

        # Error response
        error_response = APIResponse[None](success=False, error="Something went wrong")  # type: ignore[type-var]
        assert error_response.success is False
        assert error_response.data is None
        assert error_response.error == "Something went wrong"

        # Test timestamp serialization
        json_data = response.model_dump(mode="json")
        assert "timestamp" in json_data
        assert isinstance(json_data["timestamp"], str)

    def test_error_response(self) -> None:
        """Test standardized error response."""
        error = ErrorResponse(
            type="https://example.com/errors/validation",
            title="Validation Error",
            status=400,
            detail="Field 'name' is required",
            instance="https://example.com/requests/123",
        )

        assert error.type == "https://example.com/errors/validation"
        assert error.title == "Validation Error"
        assert error.status == 400
        assert error.detail == "Field 'name' is required"
        assert error.instance == "https://example.com/requests/123"


class TestCustomFieldTypes:
    """Test COS-specific custom field types."""

    def test_cos_email_str(self) -> None:
        """Test COSEmailStr validation and normalization."""
        # Valid email
        email = COSEmailStr.validate("Test@Example.COM")
        assert email == "test@example.com"  # Normalized to lowercase

        # Invalid email
        with pytest.raises(ValueError) as exc_info:
            COSEmailStr.validate("invalid-email")
        assert "Invalid email format" in str(exc_info.value)

        # Empty email
        with pytest.raises(ValueError) as exc_info:
            COSEmailStr.validate("")
        assert "Email must be a non-empty string" in str(exc_info.value)

    def test_cos_module_name(self) -> None:
        """Test COSModuleName validation."""
        # Valid module name
        name = COSModuleName.validate("Valid_Module123")
        assert name == "valid_module123"  # Normalized to lowercase

        # Invalid characters
        with pytest.raises(ValueError) as exc_info:
            COSModuleName.validate("invalid-module")
        assert "must contain only alphanumeric characters and underscores" in str(exc_info.value)

        # Must start with letter
        with pytest.raises(ValueError) as exc_info:
            COSModuleName.validate("123invalid")
        assert "must start with a letter" in str(exc_info.value)

        # Empty name
        with pytest.raises(ValueError) as exc_info:
            COSModuleName.validate("")
        assert "must be a non-empty string" in str(exc_info.value)


class TestModelTestBase:
    """Test the testing utilities provided."""

    def test_assert_validation_error(self) -> None:
        """Test validation error assertion utility."""

        class TestModel(COSBaseModel):
            name: str
            age: int = Field(ge=0)

        # Should assert correctly for validation errors
        ModelTestBase.assert_validation_error(
            TestModel,
            {"name": "", "age": -1},
            1,  # Only age validation fails (name is stripped but empty string is valid)
        )

        # Should fail if expected error count doesn't match
        with pytest.raises(AssertionError):
            ModelTestBase.assert_validation_error(
                TestModel,
                {"name": "", "age": -1},
                2,  # Wrong count - actually only 1 error occurs
            )

    def test_assert_serialization_roundtrip(self) -> None:
        """Test serialization roundtrip assertion utility."""

        class TestModel(COSBaseModel):
            name: str
            value: int
            timestamp: datetime

        model = TestModel(name="test", value=42, timestamp=datetime.now(UTC))

        # Should pass for valid roundtrip
        ModelTestBase.assert_serialization_roundtrip(model)

        # Test with a model that would fail roundtrip
        class BadModel(BaseModel):
            # This would fail roundtrip due to datetime serialization issues
            timestamp: datetime

            def model_dump(self, **kwargs: Any) -> dict[str, Any]:
                # Intentionally break serialization
                return {"timestamp": "not-a-datetime"}

        bad_model = BadModel(timestamp=datetime.now(UTC))

        with pytest.raises(ValidationError):
            ModelTestBase.assert_serialization_roundtrip(bad_model)


class TestIntegrationExamples:
    """Test the pattern with real-world usage examples."""

    def test_user_model_example(self) -> None:
        """Test a realistic user model implementation."""

        class UserCreateRequest(COSAPIModel):
            name: NameField
            email: EmailField  # Use the simpler EmailField instead
            age: int = Field(..., ge=13, le=120, description="User age")

            @field_validator("name")
            @classmethod
            def validate_name(cls, v: str) -> str:
                if not v.strip():
                    raise ValueError("Name cannot be empty")
                return v.title()

        class UserResponse(COSDBModel, SQLAlchemyIntegrationMixin):
            id: UUIDField
            name: str
            email: str
            age: int
            created_at: TimestampField

        # Test creation and validation
        user_data = {"name": "john doe", "email": "john@example.com", "age": 30}

        create_request = UserCreateRequest(**user_data)
        assert create_request.email == "john@example.com"

        # Test response model
        response_data = {
            "id": uuid4(),
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "created_at": datetime.now(UTC),
        }

        user_response = UserResponse(**response_data)
        assert isinstance(user_response.id, UUID)
        assert isinstance(user_response.created_at, datetime)

        # Test serialization
        ModelTestBase.assert_serialization_roundtrip(create_request)
        ModelTestBase.assert_serialization_roundtrip(user_response)

    def test_configuration_model_example(self) -> None:
        """Test a realistic configuration model."""

        class DatabaseConfig(COSConfigModel):
            host: str = Field(default="localhost")
            port: int = Field(default=5432, ge=1, le=65535)
            username: str
            password: str = Field(..., repr=False)
            database: str

        config = DatabaseConfig(
            username="test_user",  # Test case insensitive
            password="secret",
            database="test_db",
            unknown_field="ignored",  # Should be ignored
        )

        assert config.host == "localhost"  # Default
        assert config.port == 5432  # Default
        assert config.username == "test_user"
        assert config.password == "secret"
        assert config.database == "test_db"

        # Test that password is not in repr
        repr_str = repr(config)
        assert "secret" not in repr_str


class TestPatternCoverage:
    """Test edge cases and ensure comprehensive coverage."""

    def test_field_validator_coverage(self) -> None:
        """Test that field validators work when applied to models."""

        class TestUUIDModel(COSBaseModel):
            id: UUID

            @field_validator("id", mode="before")
            @classmethod
            def validate_id(cls, value: Any) -> Any:
                return str(value) if value is not None else value

        test_uuid = uuid4()
        model = TestUUIDModel(id=test_uuid)
        assert model.id == test_uuid

        # Test string UUID conversion
        model2 = TestUUIDModel(id=str(test_uuid))
        assert model2.id == test_uuid

    def test_inheritance_combinations(self) -> None:
        """Test various inheritance combinations."""

        class MultiInheritanceModel(COSDBModel, SQLAlchemyIntegrationMixin, PerformanceOptimizedMixin):
            id: UUID
            name: str
            value: int

        model = MultiInheritanceModel(id=uuid4(), name="test", value=42)

        # Should have all mixin methods available
        assert hasattr(model, "from_sqlalchemy")
        assert hasattr(model, "to_json_bytes")
        assert hasattr(model, "to_dict_exclude_none")

        # Test that all methods work
        json_bytes = model.to_json_bytes()
        assert isinstance(json_bytes, bytes)

        dict_data = model.to_sqlalchemy_dict()
        assert "id" in dict_data
        assert "name" in dict_data
        assert "value" in dict_data

    def test_performance_edge_cases(self) -> None:
        """Test performance-related edge cases."""

        class EdgeCaseModel(COSBaseModel):
            nullable_field: str | None = None
            list_field: list[str] = Field(default_factory=list)
            dict_field: dict[str, Any] = Field(default_factory=dict)

        model = EdgeCaseModel()

        # Test serialization with None values
        data = model.model_dump(exclude_none=True)
        assert "nullable_field" not in data

        # Test with actual values
        model.nullable_field = "not none"
        model.list_field = ["a", "b", "c"]
        model.dict_field = {"key": "value"}

        data = model.model_dump()
        assert data["nullable_field"] == "not none"
        assert data["list_field"] == ["a", "b", "c"]
        assert data["dict_field"] == {"key": "value"}
