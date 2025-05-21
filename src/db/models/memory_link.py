# src/db/models/memory_link.py

from typing import Any, ClassVar

from sqlalchemy import Column, DateTime, Integer, String, func

from src.db.base import Base


class MemoryLink(Base):
    __tablename__ = "memory_link"
    __table_args__: ClassVar[dict[str, Any]] = {"schema": "cc"}  # type: ignore[misc]

    id = Column(Integer, primary_key=True, index=True)
    source_node = Column(String(255), nullable=False)
    target_node = Column(String(255), nullable=False)
    link_type = Column(String(100), nullable=False)
    rationale = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
