# src/db/schemas/event_trace.py

from datetime import datetime

from pydantic import BaseModel


class EventTraceBase(BaseModel):
    trigger: str
    context: str | None = None
    related_prd_id: int | None = None


class EventTraceCreate(EventTraceBase):
    pass


class EventTraceInDBBase(EventTraceBase):
    id: int
    created_at: datetime | None

    class Config:
        orm_mode = True


class EventTrace(EventTraceInDBBase):
    pass
