"""Pydantic schemas for request and response validation in the Control Center module.

This file contains all the data models used for API request validation
and response formatting, ensuring type safety and data integrity.

Updated to COS Gold Standard - Pattern: /src/core_v2/patterns/model.py
"""

# MDC: cc_module
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_serializer, field_validator

# COS Gold Standard imports
from src.core_v2.patterns.model import (
    COSAPIModel,
    COSDBModel,
    NameField,
    PerformanceOptimizedMixin,
    SQLAlchemyIntegrationMixin,
)


# Health Check Schema
class HealthStatus(COSAPIModel):
    """Model for health status response."""

    status: Literal["healthy", "degraded", "offline"] = Field(
        default="healthy", description="The operational status of the service."
    )


# Health Status Database Record Schema
class HealthStatusResponse(COSDBModel, SQLAlchemyIntegrationMixin):
    """Model for health status database record response."""

    id: str = Field(..., description="Unique identifier for the health status record.")
    module: NameField = Field(..., description="The name of the module.")
    status: str = Field(..., description="The operational status of the module.")
    last_updated: datetime = Field(..., description="Timestamp of the last status update.")
    details: str | None = Field(None, description="Additional details about the status.")

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, value: Any) -> str:
        """Convert UUID to string if needed."""
        return str(value)

    @field_serializer("last_updated")
    def serialize_last_updated(self, value: datetime) -> str:
        """Serialize datetime to ISO-8601 string."""
        return value.isoformat()


# Configuration Schema
class CCConfig(COSAPIModel):
    """Model for the CC configuration response."""

    version: str = Field(default="0.1.0", description="The version of the Control Center module.")
    modules_loaded: list[str] = Field(default=["cc"], description="List of modules currently loaded.")


# Module Health Schema
class ModuleHealthStatus(COSAPIModel):
    """Model for an individual module's health status."""

    module: NameField = Field(..., description="The name of the module.")
    status: Literal["healthy", "degraded", "offline"] = Field(..., description="The operational status of the module.")
    last_updated: str = Field(..., description="ISO-8601 timestamp of the last status update.")


# System Health Report Schema
class SystemHealthReport(COSAPIModel):
    """Model for the complete system health report."""

    overall_status: Literal["healthy", "degraded", "offline"] = Field(
        ..., description="The overall status of the entire system."
    )
    modules: list[ModuleHealthStatus] = Field(..., description="Health status of individual modules.")
    timestamp: str = Field(..., description="ISO-8601 timestamp when the report was generated.")


# Module Ping Request Schema
class ModulePingRequest(COSAPIModel):
    """Model for module ping request."""

    module: NameField = Field(..., description="The name of the module to ping.")


# Module Ping Response Schema
class ModulePingResponse(COSAPIModel):
    """Model for module ping response."""

    module: NameField = Field(..., description="The name of the module that was pinged.")
    status: Literal["healthy", "degraded", "offline", "unknown"] = Field(
        ..., description="The operational status of the module."
    )
    latency_ms: int = Field(..., description="Round-trip latency in milliseconds.")


# Module CRUD Schemas
class ModuleBase(COSAPIModel):
    """Base schema for module data."""

    name: NameField = Field(..., description="The name of the module.")
    version: str = Field(..., description="The version of the module.", min_length=1, max_length=50)
    config: str | None = Field(None, description="Optional JSON configuration string for the module.")


class ModuleCreate(ModuleBase):
    """Schema for creating a new module."""

    pass


class ModuleUpdate(COSAPIModel):
    """Schema for updating an existing module."""

    name: NameField | None = Field(None, description="The name of the module.")
    version: str | None = Field(None, description="The version of the module.", min_length=1, max_length=50)
    active: bool | None = Field(None, description="Whether the module is active.")
    config: str | None = Field(None, description="Optional JSON configuration string for the module.")


class Module(ModuleBase, SQLAlchemyIntegrationMixin):
    """Schema for module response."""

    id: str = Field(..., description="Unique identifier for the module.")
    active: bool = Field(..., description="Whether the module is active.")
    last_active: datetime = Field(..., description="Timestamp of when the module was last active.")

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, value: Any) -> str:
        """Convert UUID to string if needed."""
        return str(value)

    @field_serializer("last_active")
    def serialize_last_active(self, value: datetime) -> str:
        """Serialize datetime to ISO-8601 string."""
        return value.isoformat()


# Scratch Note Schemas (Task 10)
class ScratchNoteCreate(COSAPIModel):
    """Schema for creating a new scratch note."""

    key: NameField = Field(..., description="Unique key for the scratch note.")
    content: str | None = Field(None, description="Optional content for the scratch note.")
    ttl_days: int | None = Field(None, description="Time-to-live in days (null = never expires).", ge=1, le=365)


class ScratchNoteUpdate(COSAPIModel):
    """Schema for updating an existing scratch note."""

    content: str | None = Field(None, description="Updated content for the scratch note.")
    ttl_days: int | None = Field(None, description="Updated TTL in days (null = never expires).", ge=1, le=365)


class ScratchNoteResponse(COSDBModel, SQLAlchemyIntegrationMixin):
    """Schema for scratch note response."""

    id: int = Field(..., description="Unique identifier for the scratch note.")
    key: NameField = Field(..., description="Unique key for the scratch note.")
    content: str | None = Field(None, description="Content of the scratch note.")
    created_at: datetime = Field(..., description="Timestamp when the note was created.")
    expires_at: datetime | None = Field(None, description="Timestamp when the note expires (null = never).")
    is_expired: bool = Field(..., description="Whether the note has expired.")

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        """Serialize datetime to ISO-8601 string."""
        return value.isoformat()

    @field_serializer("expires_at")
    def serialize_expires_at(self, value: datetime | None) -> str | None:
        """Serialize datetime to ISO-8601 string."""
        return value.isoformat() if value else None


class ScratchStatsResponse(COSAPIModel):
    """Schema for scratch notes statistics response."""

    total_notes: int = Field(..., description="Total number of scratch notes.")
    active_notes: int = Field(..., description="Number of active (non-expired) notes.")
    expired_notes: int = Field(..., description="Number of expired notes.")
    timestamp: str = Field(..., description="ISO-8601 timestamp when stats were generated.")
    ttl_settings: dict[str, Any] = Field(..., description="Current TTL configuration settings.")


class CleanupResponse(COSAPIModel):
    """Schema for cleanup operation response."""

    status: str = Field(..., description="Status of the cleanup operation.")
    deleted: int = Field(..., description="Number of records deleted.")
    batch_size: int | None = Field(None, description="Batch size used for cleanup.")
    expired_before: int | None = Field(None, description="Number of expired notes before cleanup.")
    total_before: int | None = Field(None, description="Total number of notes before cleanup.")
    remaining_after: int | None = Field(None, description="Number of notes remaining after cleanup.")
    timestamp: str | None = Field(None, description="ISO-8601 timestamp when cleanup completed.")
    execution_time_ms: float | None = Field(None, description="Execution time in milliseconds.")


class DebugLogRequest(COSAPIModel):
    """Request model for the debug logging endpoint."""

    event_type: str = Field(..., description="Type of event being logged", max_length=100)
    payload: dict[str, Any] | None = Field(None, description="Optional JSON payload for event data")
    prompt_data: dict[str, Any] | None = Field(None, description="Optional prompt trace data")
    request_id: str | None = Field(None, description="Optional request ID (uses context value if omitted)")
    trace_id: str | None = Field(None, description="Optional Logfire trace ID")


class DebugLogResponse(COSAPIModel, PerformanceOptimizedMixin):
    """Response model for the debug logging endpoint."""

    success: bool = Field(..., description="Whether the logging operation succeeded")
    message: str = Field(..., description="Human-readable status message")
    log_ids: dict[str, UUID] = Field(..., description="UUIDs of created log records")
    performance_ms: float = Field(..., description="Execution time in milliseconds")
    redis_validation: "RedisValidationInfo" = Field(..., description="Redis publishing validation results")


class RedisValidationInfo(COSAPIModel):
    """Redis validation information for debug endpoints."""

    publish_success: bool = Field(..., description="Whether Redis message publishing succeeded")
    published_message: dict[str, Any] | None = Field(None, description="The actual message published to Redis")
    redis_latency_ms: float | None = Field(None, description="Redis operation latency in milliseconds")
    connection_status: Literal["connected", "disconnected", "error"] = Field(..., description="Redis connection status")
    error_details: str | None = Field(None, description="Error details if publishing failed")


class ConnectionPoolStatus(COSAPIModel):
    """Redis connection pool status information."""

    max_connections: int = Field(..., description="Maximum number of connections in the pool")
    active_connections: int = Field(..., description="Number of currently active connections")
    idle_connections: int = Field(..., description="Number of idle connections available")
    status: Literal["connected", "disconnected", "error"] = Field(..., description="Overall pool status")


class RedisPerformanceMetrics(COSAPIModel):
    """Redis performance metrics for monitoring."""

    ping_latency_ms: float | None = Field(None, description="Redis ping latency in milliseconds")
    last_successful_operation: str | None = Field(None, description="ISO-8601 timestamp of last successful operation")
    operations_per_second: float | None = Field(None, description="Recent operations per second")
    error_rate: float | None = Field(None, description="Error rate as a percentage")


class RedisHealthResponse(COSAPIModel, PerformanceOptimizedMixin):
    """Comprehensive Redis health status response."""

    status: Literal["healthy", "degraded", "offline"] = Field(..., description="Overall Redis health status")
    timestamp: str = Field(..., description="ISO-8601 timestamp when health check was performed")
    connection_pool: ConnectionPoolStatus = Field(..., description="Connection pool status information")
    performance_metrics: RedisPerformanceMetrics = Field(..., description="Performance metrics and benchmarks")
    redis_info: dict[str, Any] = Field(..., description="Redis server information and statistics")
    circuit_breaker: "CircuitBreakerStatus" = Field(..., description="Circuit breaker status for Redis operations")
    error: str | None = Field(None, description="Error message if Redis is unavailable")


# Enhanced Health Schemas for Circuit Breaker and DLQ Metrics
class CircuitBreakerStatus(COSAPIModel):
    """Model for circuit breaker status metrics."""

    state: Literal["CLOSED", "OPEN", "HALF_OPEN"] = Field(..., description="Current state of the circuit breaker")
    failure_count: int = Field(..., description="Number of consecutive failures")
    last_failure_time: str | None = Field(None, description="ISO-8601 timestamp of the last failure")
    next_attempt_time: str | None = Field(
        None, description="ISO-8601 timestamp when next attempt is allowed (OPEN state)"
    )


class DLQMetrics(COSAPIModel):
    """Model for Dead Letter Queue metrics."""

    size: int = Field(..., description="Number of messages currently in the DLQ")
    channel: NameField = Field(..., description="DLQ channel name")
    oldest_message_time: str | None = Field(None, description="ISO-8601 timestamp of the oldest message in DLQ")
    newest_message_time: str | None = Field(None, description="ISO-8601 timestamp of the newest message in DLQ")


class EnhancedHealthResponse(COSAPIModel, PerformanceOptimizedMixin):
    """Enhanced health response with circuit breaker and DLQ metrics."""

    status: Literal["healthy", "degraded", "offline"] = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="ISO-8601 timestamp when the health check was performed")
    circuit_breaker_state: CircuitBreakerStatus = Field(..., description="Circuit breaker status metrics")
    dlq_metrics: list[DLQMetrics] = Field(..., description="Dead Letter Queue metrics for all monitored channels")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    redis_connected: bool = Field(..., description="Whether Redis connection is active")
    qdrant_status: dict[str, Any] | None = Field(
        default=None, description="Qdrant vector database status (optional service)"
    )
