# src/db/schemas/memory_link.py

from datetime import datetime

from pydantic import BaseModel


class MemoryLinkBase(BaseModel):
    source_node: str
    target_node: str
    link_type: str
    rationale: str | None = None


class MemoryLinkCreate(MemoryLinkBase):
    pass


class MemoryLinkInDBBase(MemoryLinkBase):
    id: int
    created_at: datetime | None

    class Config:
        orm_mode = True


class MemoryLink(MemoryLinkInDBBase):
    pass
