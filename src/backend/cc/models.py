"""SQLAlchemy models for the Control Center module.

This file contains the database models for the CC module,
using SQLAlchemy's declarative syntax with Table Args for schema isolation.
"""

# MDC: cc_module
from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as POSTGRES_UUID
from sqlalchemy.orm import declarative_base

# Base class for declarative models
Base = declarative_base()
DeclarativeBase = Any  # Type alias for SQLAlchemy declarative base


class HealthStatus(Base):  # type: ignore[misc, valid-type]
    """Health status record for a system module.

    This model tracks the health status of each module in the system,
    with a timestamp for the last update and the current operational status.
    """

    __tablename__: ClassVar[str] = "health_status"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "cc"}

    id = Column(POSTGRES_UUID, primary_key=True, default=uuid4)
    module = Column(String, nullable=False, unique=True, index=True)
    status = Column(String, nullable=False)
    last_updated = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    details = Column(String, nullable=True)

    def __repr__(self) -> str:
        """Return string representation of HealthStatus."""
        return f"<HealthStatus(module='{self.module}', status='{self.status}')>"


class Module(Base):  # type: ignore[misc, valid-type]
    """Module configuration record.

    This model stores information about modules in the system,
    including their configuration, version, and activation status.
    """

    __tablename__: ClassVar[str] = "modules"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "cc"}

    id = Column(POSTGRES_UUID, primary_key=True, default=uuid4)
    name = Column(String, nullable=False, unique=True, index=True)
    version = Column(String, nullable=False)
    active = Column(String, nullable=False, default=True)
    last_active = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    config = Column(String, nullable=True)  # JSON string

    def __repr__(self) -> str:
        """Return string representation of Module object."""
        return (
            f"<Module(name='{self.name}', "
            f"version='{self.version}', "
            f"active={self.active})>"
        )
