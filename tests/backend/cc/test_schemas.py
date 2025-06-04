"""Tests for the Control Center Pydantic schemas.

This file contains unit tests for the Pydantic models used in the CC module.
"""

from __future__ import annotations

# MDC: cc_module
import pytest
from pydantic import ValidationError

from src.backend.cc.schemas import (
    CCConfig,
    HealthStatus,
    ModuleHealthStatus,
    ModulePingRequest,
    ModulePingResponse,
    SystemHealthReport,
)


def test_health_status_schema() -> None:
    """Test the HealthStatus schema."""
    # Create a valid instance
    health = HealthStatus(status="healthy")

    # Verify the default value
    assert health.status == "healthy"

    # Test serialization
    serialized = health.model_dump()
    assert serialized == {"status": "healthy"}

    # Test that invalid status raises an error
    with pytest.raises(ValidationError):
        HealthStatus(status="invalid_status")  # type: ignore# type: ignore  # TODO: temp ignore — remove after refactor[arg-type]


def test_ccconfig_schema() -> None:
    """Test the CCConfig schema."""
    # Create a valid instance
    config = CCConfig(version="0.1.0", modules_loaded=["cc", "mem0"])

    # Verify the values
    assert config.version == "0.1.0"
    assert config.modules_loaded == ["cc", "mem0"]

    # Test serialization
    serialized = config.model_dump()
    assert serialized == {"version": "0.1.0", "modules_loaded": ["cc", "mem0"]}


def test_module_health_status_schema() -> None:
    """Test the ModuleHealthStatus schema."""
    # Create a valid instance
    module_health = ModuleHealthStatus(module="cc", status="healthy", last_updated="2025-04-02T10:00:00Z")

    # Verify the values
    assert module_health.module == "cc"
    assert module_health.status == "healthy"
    assert module_health.last_updated == "2025-04-02T10:00:00Z"

    # Test serialization
    serialized = module_health.model_dump()
    assert serialized == {
        "module": "cc",
        "status": "healthy",
        "last_updated": "2025-04-02T10:00:00Z",
    }

    # Test that invalid status raises an error
    with pytest.raises(ValidationError):
        ModuleHealthStatus(
            module="cc",
            status="invalid_status",  # type: ignore# type: ignore  # TODO: temp ignore — remove after refactor[arg-type]
            last_updated="2025-04-02T10:00:00Z",
        )


def test_system_health_report_schema() -> None:
    """Test the SystemHealthReport schema."""
    # Create a valid instance
    report = SystemHealthReport(
        overall_status="healthy",
        modules=[
            ModuleHealthStatus(module="cc", status="healthy", last_updated="2025-04-02T10:00:00Z"),
            ModuleHealthStatus(module="mem0", status="healthy", last_updated="2025-04-02T09:55:00Z"),
        ],
        timestamp="2025-04-02T10:15:00Z",
    )

    # Verify the values
    assert report.overall_status == "healthy"
    assert len(report.modules) == 2
    assert report.modules[0].module == "cc"
    assert report.timestamp == "2025-04-02T10:15:00Z"

    # Test serialization
    serialized = report.model_dump()
    assert serialized["overall_status"] == "healthy"
    assert len(serialized["modules"]) == 2
    assert serialized["timestamp"] == "2025-04-02T10:15:00Z"


def test_module_ping_request_schema() -> None:
    """Test the ModulePingRequest schema."""
    # Create a valid instance
    request = ModulePingRequest(module="cc")

    # Verify the value
    assert request.module == "cc"

    # Test serialization
    serialized = request.model_dump()
    assert serialized == {"module": "cc"}

    # Test that missing module raises an error
    with pytest.raises(ValidationError):
        ModulePingRequest()  # type: ignore# type: ignore  # TODO: temp ignore — remove after refactor[call-arg]


def test_module_ping_response_schema() -> None:
    """Test the ModulePingResponse schema."""
    # Create a valid instance
    response = ModulePingResponse(module="cc", status="healthy", latency_ms=5)

    # Verify the values
    assert response.module == "cc"
    assert response.status == "healthy"
    assert response.latency_ms == 5

    # Test serialization
    serialized = response.model_dump()
    assert serialized == {"module": "cc", "status": "healthy", "latency_ms": 5}

    # Test that invalid status raises an error
    with pytest.raises(ValidationError):
        ModulePingResponse(
            module="cc",
            status="invalid_status",  # type: ignore# type: ignore  # TODO: temp ignore — remove after refactor[arg-type]
            latency_ms=5,
        )
