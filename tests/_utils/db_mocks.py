"""Database mock helpers for testing.

This module provides proper database mock helpers that accurately simulate
SQLAlchemy 2.0 behavior for AsyncSession and Result objects.
"""

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock


class MockScalarResult:
    """Mock for SQLAlchemy ScalarResult that mimics real behavior."""

    def __init__(self, value: Any) -> None:
        """Initialize with a single value or None."""
        self._value = value

    def first(self) -> Any:
        """Get the first result from the mock scalar result."""
        return self._value

    def all(self) -> list[Any]:
        """Return all results as a list."""
        return [self._value] if self._value is not None else []

    def __iter__(self) -> Iterator[Any]:
        """Make the result iterable."""
        return iter(self.all())


def mock_execute(return_value: Any) -> MagicMock:
    """Create a properly configured mock for AsyncSession.execute().

    Args:
    ----
        return_value: The value to return from result.scalars().first()

    Returns:
    -------
        MagicMock: A mock Result object with proper scalars() behavior

    Example:
    -------
        async_session.execute.return_value = mock_execute(health_status_obj)

    """
    mock_result = MagicMock(name="AsyncResult")
    mock_result.scalars.return_value = MockScalarResult(return_value)

    # Also support scalar_one_or_none() pattern
    mock_result.scalar_one_or_none.return_value = return_value

    # Support scalar() for single value queries
    mock_result.scalar.return_value = return_value

    return mock_result


def mock_execute_multiple(return_values: list[Any]) -> MagicMock:
    """Create a mock for queries that return multiple results.

    Args:
    ----
        return_values: List of values to return from result.scalars().all()

    Returns:
    -------
        MagicMock: A mock Result object with proper scalars() behavior for multiple results

    """
    mock_result = MagicMock(name="AsyncResult")

    class MockMultipleScalarResult:
        def __init__(self, values: list[Any]) -> None:
            self._values = values

        def first(self) -> Any:
            return self._values[0] if self._values else None

        def all(self) -> list[Any]:
            return self._values

        def __iter__(self) -> Iterator[Any]:
            return iter(self._values)

    mock_result.scalars.return_value = MockMultipleScalarResult(return_values)
    mock_result.scalar_one_or_none.return_value = return_values[0] if return_values else None

    return mock_result
