"""SQLAlchemy models for the Control Center module.

This file contains the database models for the CC module,
using SQLAlchemy's declarative syntax with Table Args for schema isolation.

Enhanced with COS Gold Standard patterns for better integration
with Pydantic schemas and modern SQLAlchemy 2.0+ patterns.
"""

# MDC: cc_module
import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import TIMESTAMP, Boolean, String
from sqlalchemy.dialects.postgresql import UUID as POSTGRES_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import String as SQLString
from sqlalchemy.types import TypeDecorator

from src.db.base import Base


class UUID(TypeDecorator[str]):
    """Platform-independent UUID type.

    Uses PostgreSQL UUID when available, otherwise String.
    """

    impl = SQLString
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(POSTGRES_UUID())
        else:
            return dialect.type_descriptor(SQLString(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None or dialect.name == "postgresql":
            return value
        else:
            return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None or dialect.name == "postgresql":
            return value
        else:
            return value


def get_table_args() -> dict[str, Any]:
    """Get table args based on database type."""
    # Only use schema for PostgreSQL
    if os.getenv("ENABLE_DB_INTEGRATION", "0") == "1":
        return {"schema": "cc", "extend_existing": True}
    else:
        return {"extend_existing": True}


class HealthStatus(Base):
    """Health status record for a system module.

    This model tracks the health status of each module in the system,
    with a timestamp for the last update and the current operational status.

    Enhanced with better type annotations while maintaining compatibility.
    """

    __tablename__ = "health_status"
    __table_args__ = get_table_args()

    # Enhanced with type annotations but maintaining backward compatibility
    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=lambda: str(uuid4()))
    module: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    last_updated: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    details: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    def __init__(self, **kwargs: Any) -> None:
        """Initialize HealthStatus with defaults."""
        # Apply defaults if not provided
        if "id" not in kwargs:
            kwargs["id"] = str(uuid4())
        if "last_updated" not in kwargs:
            kwargs["last_updated"] = datetime.now(UTC)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """Return string representation of HealthStatus."""
        return f"<HealthStatus(module='{self.module}', status='{self.status}')>"


class Module(Base):
    """Module configuration record.

    This model stores information about modules in the system,
    including their configuration, version, and activation status.

    Enhanced with better type annotations while maintaining compatibility.
    """

    __tablename__ = "modules"
    __table_args__ = get_table_args()

    # Enhanced with type annotations but maintaining backward compatibility
    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_active: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    config: Mapped[str | None] = mapped_column(String(2000), nullable=True)  # JSON string

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Module with defaults."""
        # Apply defaults if not provided
        if "id" not in kwargs:
            kwargs["id"] = str(uuid4())
        if "active" not in kwargs:
            kwargs["active"] = True
        if "last_active" not in kwargs:
            kwargs["last_active"] = datetime.now(UTC)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """Return string representation of Module object."""
        return f"<Module(name='{self.name}', version='{self.version}', active={self.active})>"
