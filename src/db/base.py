# src/db/base.py

from typing import ClassVar, Protocol

from sqlalchemy.orm import DeclarativeBase as SQLAlchemyBase


# Define a protocol for SQLAlchemy Base classes
class DeclarativeBaseProtocol(Protocol):
    __abstract__: ClassVar[bool]
    __tablename__: ClassVar[str]
    __table_args__: ClassVar[dict[str, str]]


class Base(SQLAlchemyBase):
    """Base class for all models."""

    __abstract__ = True
    pass
