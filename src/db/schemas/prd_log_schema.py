# src/db/schemas/prd_log.py

from datetime import datetime

from pydantic import BaseModel


class PRDLogBase(BaseModel):
    title: str
    summary: str | None = None
    source: str | None = None
    category: str | None = None


class PRDLogCreate(PRDLogBase):
    pass


class PRDLogUpdate(PRDLogBase):
    pass


class PRDLogInDBBase(PRDLogBase):
    id: int
    created_at: datetime | None
    updated_at: datetime | None

    class Config:
        orm_mode = True


class PRDLog(PRDLogInDBBase):
    pass
