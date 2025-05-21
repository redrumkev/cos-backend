# src/db/models/event_trace.py

from typing import Any, ClassVar

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from src.db.base import Base


class EventTrace(Base):
    __tablename__ = "event_trace"
    __table_args__: ClassVar[dict[str, Any]] = {"schema": "cc"}  # type: ignore[misc]

    id = Column(Integer, primary_key=True, index=True)
    trigger = Column(String(255), nullable=False)
    context = Column(Text, nullable=True)
    related_prd_id = Column(Integer, ForeignKey("cc.prd_log.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
