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


# Configuration Schema
class CCConfig(BaseModel):
    """Model for the CC configuration response."""

    version: str = Field(
        default="0.1.0", description="The version of the Control Center module."
    )
    modules_loaded: list[str] = Field(
        default=["cc"], description="List of modules currently loaded."
    )
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"version": "0.1.0", "modules_loaded": ["cc", "mem0"]}
        }
    )


# Module Health Schema
class ModuleHealthStatus(BaseModel):
    """Model for an individual module's health status."""

    module: str = Field(..., description="The name of the module.")
    status: Literal["healthy", "degraded", "offline"] = Field(
        ..., description="The operational status of the module."
    )
    last_updated: str = Field(
        ..., description="ISO-8601 timestamp of the last status update."
    )

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
    modules: list[ModuleHealthStatus] = Field(
        ..., description="Health status of individual modules."
    )
    timestamp: str = Field(
        ..., description="ISO-8601 timestamp when the report was generated."
    )

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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"module": "mem0", "status": "healthy", "latency_ms": 5}
        }
    )
