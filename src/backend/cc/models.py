"""SQLAlchemy models for the Control Center module.

This file contains the database models for the CC module,
using SQLAlchemy's declarative syntax with Table Args for schema isolation.
"""

# MDC: cc_module
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as POSTGRES_UUID

from src.db.base import Base


class HealthStatus(Base):
    """Health status record for a system module.

    This model tracks the health status of each module in the system,
    with a timestamp for the last update and the current operational status.
    """

    __tablename__ = "health_status"
    __table_args__ = {"schema": "cc", "extend_existing": True}  # noqa: RUF012

    id = Column(POSTGRES_UUID, primary_key=True, default=uuid4)
    module = Column(String, nullable=False, unique=True, index=True)
    status = Column(String, nullable=False)
    last_updated = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    details = Column(String, nullable=True)

    def __repr__(self) -> str:
        """Return string representation of HealthStatus."""
        return f"<HealthStatus(module='{self.module}', status='{self.status}')>"


class Module(Base):
    """Module configuration record.

    This model stores information about modules in the system,
    including their configuration, version, and activation status.
    """

    __tablename__ = "modules"
    __table_args__ = {"schema": "cc", "extend_existing": True}  # noqa: RUF012

    id = Column(POSTGRES_UUID, primary_key=True, default=uuid4)
    name = Column(String, nullable=False, unique=True, index=True)
    version = Column(String, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    last_active = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    config = Column(String, nullable=True)  # JSON string

    def __repr__(self) -> str:
        """Return string representation of Module object."""
        return f"<Module(name='{self.name}', version='{self.version}', active={self.active})>"
