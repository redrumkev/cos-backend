"""Pydantic schemas for request and response validation in the Control Center module.

This file contains all the data models used for API request validation
and response formatting, ensuring type safety and data integrity.
"""

# MDC: cc_module
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


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

    module: str = Field(..., description="The name of the module to ping.", min_length=1)

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


# Scratch Note Schemas (Task 10)
class ScratchNoteCreate(BaseModel):
    """Schema for creating a new scratch note."""

    key: str = Field(..., description="Unique key for the scratch note.", min_length=1, max_length=255)
    content: str | None = Field(None, description="Optional content for the scratch note.")
    ttl_days: int | None = Field(None, description="Time-to-live in days (null = never expires).", ge=1, le=365)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"key": "user_session_123", "content": "Temporary user session data", "ttl_days": 7}
        }
    )


class ScratchNoteUpdate(BaseModel):
    """Schema for updating an existing scratch note."""

    content: str | None = Field(None, description="Updated content for the scratch note.")
    ttl_days: int | None = Field(None, description="Updated TTL in days (null = never expires).", ge=1, le=365)

    model_config = ConfigDict(json_schema_extra={"example": {"content": "Updated session data", "ttl_days": 14}})


class ScratchNoteResponse(BaseModel):
    """Schema for scratch note response."""

    id: int = Field(..., description="Unique identifier for the scratch note.")
    key: str = Field(..., description="Unique key for the scratch note.")
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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "key": "user_session_123",
                "content": "Temporary user session data",
                "created_at": "2025-04-02T10:00:00Z",
                "expires_at": "2025-04-09T10:00:00Z",
                "is_expired": False,
            }
        },
    )


class ScratchStatsResponse(BaseModel):
    """Schema for scratch notes statistics response."""

    total_notes: int = Field(..., description="Total number of scratch notes.")
    active_notes: int = Field(..., description="Number of active (non-expired) notes.")
    expired_notes: int = Field(..., description="Number of expired notes.")
    timestamp: str = Field(..., description="ISO-8601 timestamp when stats were generated.")
    ttl_settings: dict[str, Any] = Field(..., description="Current TTL configuration settings.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_notes": 150,
                "active_notes": 120,
                "expired_notes": 30,
                "timestamp": "2025-04-02T10:00:00Z",
                "ttl_settings": {"default_ttl_days": 7, "cleanup_enabled": True, "cleanup_batch_size": 1000},
            }
        }
    )


class CleanupResponse(BaseModel):
    """Schema for cleanup operation response."""

    status: str = Field(..., description="Status of the cleanup operation.")
    deleted: int = Field(..., description="Number of records deleted.")

    model_config = ConfigDict(json_schema_extra={"example": {"status": "completed", "deleted": 25}})


class DebugLogRequest(BaseModel):
    """Request model for the debug logging endpoint."""

    event_type: str = Field(..., description="Type of event being logged", max_length=100)
    payload: dict[str, Any] | None = Field(None, description="Optional JSON payload for event data")
    prompt_data: dict[str, Any] | None = Field(None, description="Optional prompt trace data")
    request_id: str | None = Field(None, description="Optional request ID (uses context value if omitted)")
    trace_id: str | None = Field(None, description="Optional Logfire trace ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_type": "debug_test",
                "payload": {"message": "Test debug log", "level": "INFO"},
                "prompt_data": {
                    "prompt_text": "Debug logging test",
                    "response_text": "Successfully logged",
                    "execution_time_ms": 150,
                    "token_count": 25,
                },
            }
        }
    )


class DebugLogResponse(BaseModel):
    """Response model for the debug logging endpoint."""

    success: bool = Field(..., description="Whether the logging operation succeeded")
    message: str = Field(..., description="Human-readable status message")
    log_ids: dict[str, UUID] = Field(..., description="UUIDs of created log records")
    performance_ms: float = Field(..., description="Execution time in milliseconds")
    redis_validation: "RedisValidationInfo" = Field(..., description="Redis publishing validation results")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Debug log created successfully for event_type: test_event",
                "log_ids": {
                    "base_log_id": "123e4567-e89b-12d3-a456-426614174000",
                    "event_log_id": "123e4567-e89b-12d3-a456-426614174001",
                },
                "performance_ms": 25.5,
                "redis_validation": {
                    "publish_success": True,
                    "published_message": {"type": "debug_log", "data": "..."},
                    "redis_latency_ms": 2.3,
                    "connection_status": "connected",
                },
            }
        }
    )


class RedisValidationInfo(BaseModel):
    """Redis validation information for debug endpoints."""

    publish_success: bool = Field(..., description="Whether Redis message publishing succeeded")
    published_message: dict[str, Any] | None = Field(None, description="The actual message published to Redis")
    redis_latency_ms: float | None = Field(None, description="Redis operation latency in milliseconds")
    connection_status: Literal["connected", "disconnected", "error"] = Field(..., description="Redis connection status")
    error_details: str | None = Field(None, description="Error details if publishing failed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "publish_success": True,
                "published_message": {
                    "event_type": "debug_log",
                    "timestamp": "2025-01-14T10:00:00Z",
                    "payload": {"test": "data"},
                },
                "redis_latency_ms": 2.3,
                "connection_status": "connected",
                "error_details": None,
            }
        }
    )


class ConnectionPoolStatus(BaseModel):
    """Redis connection pool status information."""

    max_connections: int = Field(..., description="Maximum number of connections in the pool")
    active_connections: int = Field(..., description="Number of currently active connections")
    idle_connections: int = Field(..., description="Number of idle connections available")
    status: Literal["connected", "disconnected", "error"] = Field(..., description="Overall pool status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"max_connections": 10, "active_connections": 2, "idle_connections": 8, "status": "connected"}
        }
    )


class RedisPerformanceMetrics(BaseModel):
    """Redis performance metrics for monitoring."""

    ping_latency_ms: float | None = Field(None, description="Redis ping latency in milliseconds")
    last_successful_operation: str | None = Field(None, description="ISO-8601 timestamp of last successful operation")
    operations_per_second: float | None = Field(None, description="Recent operations per second")
    error_rate: float | None = Field(None, description="Error rate as a percentage")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ping_latency_ms": 1.2,
                "last_successful_operation": "2025-01-14T10:00:00Z",
                "operations_per_second": 150.5,
                "error_rate": 0.01,
            }
        }
    )


class RedisHealthResponse(BaseModel):
    """Comprehensive Redis health status response."""

    status: Literal["healthy", "degraded", "offline"] = Field(..., description="Overall Redis health status")
    timestamp: str = Field(..., description="ISO-8601 timestamp when health check was performed")
    connection_pool: ConnectionPoolStatus = Field(..., description="Connection pool status information")
    performance_metrics: RedisPerformanceMetrics = Field(..., description="Performance metrics and benchmarks")
    redis_info: dict[str, Any] = Field(..., description="Redis server information and statistics")
    circuit_breaker: "CircuitBreakerStatus" = Field(..., description="Circuit breaker status for Redis operations")
    error: str | None = Field(None, description="Error message if Redis is unavailable")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2025-01-14T10:00:00Z",
                "connection_pool": {
                    "max_connections": 10,
                    "active_connections": 2,
                    "idle_connections": 8,
                    "status": "connected",
                },
                "performance_metrics": {
                    "ping_latency_ms": 1.2,
                    "last_successful_operation": "2025-01-14T10:00:00Z",
                    "operations_per_second": 150.5,
                    "error_rate": 0.01,
                },
                "redis_info": {"redis_version": "7.0.0", "connected_clients": "5", "used_memory": "1048576"},
                "circuit_breaker": {
                    "state": "CLOSED",
                    "failure_count": 0,
                    "last_failure_time": None,
                    "next_attempt_time": None,
                },
                "error": None,
            }
        }
    )


# Enhanced Health Schemas for Circuit Breaker and DLQ Metrics
class CircuitBreakerStatus(BaseModel):
    """Model for circuit breaker status metrics."""

    state: Literal["CLOSED", "OPEN", "HALF_OPEN"] = Field(..., description="Current state of the circuit breaker")
    failure_count: int = Field(..., description="Number of consecutive failures")
    last_failure_time: str | None = Field(None, description="ISO-8601 timestamp of the last failure")
    next_attempt_time: str | None = Field(
        None, description="ISO-8601 timestamp when next attempt is allowed (OPEN state)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "state": "CLOSED",
                "failure_count": 0,
                "last_failure_time": None,
                "next_attempt_time": None,
            }
        }
    )


class DLQMetrics(BaseModel):
    """Model for Dead Letter Queue metrics."""

    size: int = Field(..., description="Number of messages currently in the DLQ")
    channel: str = Field(..., description="DLQ channel name")
    oldest_message_time: str | None = Field(None, description="ISO-8601 timestamp of the oldest message in DLQ")
    newest_message_time: str | None = Field(None, description="ISO-8601 timestamp of the newest message in DLQ")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "size": 3,
                "channel": "subscriber_dlq",
                "oldest_message_time": "2025-04-02T09:30:00Z",
                "newest_message_time": "2025-04-02T10:15:00Z",
            }
        }
    )


class EnhancedHealthResponse(BaseModel):
    """Enhanced health response with circuit breaker and DLQ metrics."""

    status: Literal["healthy", "degraded", "offline"] = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="ISO-8601 timestamp when the health check was performed")
    circuit_breaker_state: CircuitBreakerStatus = Field(..., description="Circuit breaker status metrics")
    dlq_metrics: list[DLQMetrics] = Field(..., description="Dead Letter Queue metrics for all monitored channels")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    redis_connected: bool = Field(..., description="Whether Redis connection is active")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2025-04-02T10:15:00Z",
                "circuit_breaker_state": {
                    "state": "CLOSED",
                    "failure_count": 0,
                    "last_failure_time": None,
                    "next_attempt_time": None,
                },
                "dlq_metrics": [
                    {
                        "size": 3,
                        "channel": "subscriber_dlq",
                        "oldest_message_time": "2025-04-02T09:30:00Z",
                        "newest_message_time": "2025-04-02T10:15:00Z",
                    }
                ],
                "uptime_seconds": 3600.5,
                "redis_connected": True,
            }
        }
    )
