# src/db/models/prd_log.py

from typing import Any, ClassVar

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from src.db.base import Base


class PRDLog(Base):
    __tablename__ = "prd_log"
    # adjust schema as needed per module
    __table_args__: ClassVar[dict[str, Any]] = {"schema": "cc"}  # type: ignore[misc]

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    source = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
