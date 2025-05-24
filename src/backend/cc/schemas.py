"""Pydantic schemas for request and response validation in the Control Center module.

This file contains all the data models used for API request validation
and response formatting, ensuring type safety and data integrity.
"""

# MDC: cc_module
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Health Check Schema
class HealthStatus(BaseModel):
    """Model for health status response."""

    status: Literal["healthy", "degraded", "offline"] = Field(
        default="healthy", description="The operational status of the service."
    )
    model_config = ConfigDict(json_schema_extra={"example": {"status": "healthy"}})


# Health Status Database Record Schema
class HealthStatusResponse(BaseModel):
    """Model for health status database record response."""

    id: str = Field(..., description="Unique identifier for the health status record.")
    module: str = Field(..., description="The name of the module.")
    status: str = Field(..., description="The operational status of the module.")
    last_updated: str = Field(..., description="ISO-8601 timestamp of the last status update.")
    details: str | None = Field(None, description="Additional details about the status.")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "module": "cc",
                "status": "healthy",
                "last_updated": "2025-04-02T10:00:00Z",
                "details": "All systems operational",
            }
        },
    )


# Configuration Schema
class CCConfig(BaseModel):
    """Model for the CC configuration response."""

    version: str = Field(default="0.1.0", description="The version of the Control Center module.")
    modules_loaded: list[str] = Field(default=["cc"], description="List of modules currently loaded.")
    model_config = ConfigDict(json_schema_extra={"example": {"version": "0.1.0", "modules_loaded": ["cc", "mem0"]}})


# Module Health Schema
class ModuleHealthStatus(BaseModel):
    """Model for an individual module's health status."""

    module: str = Field(..., description="The name of the module.")
    status: Literal["healthy", "degraded", "offline"] = Field(..., description="The operational status of the module.")
    last_updated: str = Field(..., description="ISO-8601 timestamp of the last status update.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "module": "cc",
                "status": "healthy",
                "last_updated": "2025-04-02T10:00:00Z",
            }
        }
    )


# System Health Report Schema
class SystemHealthReport(BaseModel):
    """Model for the complete system health report."""

    overall_status: Literal["healthy", "degraded", "offline"] = Field(
        ..., description="The overall status of the entire system."
    )
    modules: list[ModuleHealthStatus] = Field(..., description="Health status of individual modules.")
    timestamp: str = Field(..., description="ISO-8601 timestamp when the report was generated.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "overall_status": "healthy",
                "modules": [
                    {
                        "module": "cc",
                        "status": "healthy",
                        "last_updated": "2025-04-02T10:00:00Z",
                    },
                    {
                        "module": "mem0",
                        "status": "healthy",
                        "last_updated": "2025-04-02T09:55:00Z",
                    },
                ],
                "timestamp": "2025-04-02T10:15:00Z",
            }
        }
    )


# Module Ping Request Schema
class ModulePingRequest(BaseModel):
    """Model for module ping request."""

    module: str = Field(..., description="The name of the module to ping.")

    model_config = ConfigDict(json_schema_extra={"example": {"module": "mem0"}})


# Module Ping Response Schema
class ModulePingResponse(BaseModel):
    """Model for module ping response."""

    module: str = Field(..., description="The name of the module that was pinged.")
    status: Literal["healthy", "degraded", "offline", "unknown"] = Field(
        ..., description="The operational status of the module."
    )
    latency_ms: int = Field(..., description="Round-trip latency in milliseconds.")

    model_config = ConfigDict(json_schema_extra={"example": {"module": "mem0", "status": "healthy", "latency_ms": 5}})


# Module CRUD Schemas
class ModuleBase(BaseModel):
    """Base schema for module data."""

    name: str = Field(..., description="The name of the module.", min_length=1, max_length=255)
    version: str = Field(..., description="The version of the module.", min_length=1, max_length=50)
    config: str | None = Field(None, description="Optional JSON configuration string for the module.")


class ModuleCreate(ModuleBase):
    """Schema for creating a new module."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"name": "new_module", "version": "1.0.0", "config": '{"setting1": "value1"}'}}
    )


class ModuleUpdate(BaseModel):
    """Schema for updating an existing module."""

    name: str | None = Field(None, description="The name of the module.", min_length=1, max_length=255)
    version: str | None = Field(None, description="The version of the module.", min_length=1, max_length=50)
    active: bool | None = Field(None, description="Whether the module is active.")
    config: str | None = Field(None, description="Optional JSON configuration string for the module.")

    model_config = ConfigDict(
        json_schema_extra={"example": {"version": "1.1.0", "active": True, "config": '{"setting1": "new_value"}'}}
    )


class Module(ModuleBase):
    """Schema for module response."""

    id: str = Field(..., description="Unique identifier for the module.")
    active: bool = Field(..., description="Whether the module is active.")
    last_active: str = Field(..., description="ISO-8601 timestamp of when the module was last active.")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "cc",
                "version": "1.0.0",
                "active": True,
                "last_active": "2025-04-02T10:00:00Z",
                "config": '{"setting1": "value1"}',
            }
        },
    )
