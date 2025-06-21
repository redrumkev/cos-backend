"""Unit tests for mem0_models SQLAlchemy models.

Focused tests for the SQLAlchemy model layer including:
- Model instantiation with required fields
- UUID generation and defaults
- JSONB payload handling (nullable behavior)
- Timestamp automatic generation
- String representation methods

Following Task 013 proven testing patterns with realistic expectations.
"""

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.cc.mem0_models import BaseLog, EventLog, PromptTrace


class TestBaseLogModel:
    """Test BaseLog model functionality."""

    async def test_baselog_creation_with_required_fields(self, mem0_db_session: AsyncSession) -> None:
        """Test BaseLog creation with only required fields."""
        base_log = BaseLog(level="INFO", message="Test message")

        mem0_db_session.add(base_log)
        await mem0_db_session.flush()

        # Verify auto-generated fields
        assert base_log.id is not None
        assert isinstance(base_log.id, uuid.UUID)
        assert base_log.timestamp is not None
        assert isinstance(base_log.timestamp, datetime)
        assert base_log.level == "INFO"
        assert base_log.message == "Test message"
        assert base_log.payload is None  # Actual behavior: nullable

    async def test_baselog_with_payload(self, mem0_db_session: AsyncSession) -> None:
        """Test BaseLog with JSONB payload."""
        payload = {"key": "value", "number": 42}
        base_log = BaseLog(level="DEBUG", message="Test with payload", payload=payload)

        mem0_db_session.add(base_log)
        await mem0_db_session.flush()

        assert base_log.payload == payload
        assert base_log.payload["key"] == "value"
        assert base_log.payload["number"] == 42

    async def test_baselog_string_representation(self, mem0_db_session: AsyncSession) -> None:
        """Test BaseLog __repr__ method."""
        base_log = BaseLog(level="ERROR", message="Test repr")
        mem0_db_session.add(base_log)
        await mem0_db_session.flush()

        repr_str = repr(base_log)
        assert "BaseLog" in repr_str
        assert str(base_log.id) in repr_str
        assert "ERROR" in repr_str


class TestPromptTraceModel:
    """Test PromptTrace model functionality."""

    async def test_prompttrace_creation_with_required_fields(self, mem0_db_session: AsyncSession) -> None:
        """Test PromptTrace creation with required fields."""
        base_log = BaseLog(level="INFO", message="Parent log")
        mem0_db_session.add(base_log)
        await mem0_db_session.flush()

        prompt_trace = PromptTrace(base_log_id=base_log.id, prompt_text="Test prompt")
        mem0_db_session.add(prompt_trace)
        await mem0_db_session.flush()

        # Verify fields
        assert prompt_trace.id is not None
        assert isinstance(prompt_trace.id, uuid.UUID)
        assert prompt_trace.base_log_id == base_log.id
        assert prompt_trace.prompt_text == "Test prompt"
        assert prompt_trace.response_text is None
        assert prompt_trace.created_at is not None

    async def test_prompttrace_with_optional_fields(self, mem0_db_session: AsyncSession) -> None:
        """Test PromptTrace with all optional fields."""
        base_log = BaseLog(level="INFO", message="Parent log")
        mem0_db_session.add(base_log)
        await mem0_db_session.flush()

        prompt_trace = PromptTrace(
            base_log_id=base_log.id,
            prompt_text="Full prompt",
            response_text="Full response",
            execution_time_ms=150,
            token_count=100,
        )
        mem0_db_session.add(prompt_trace)
        await mem0_db_session.flush()

        assert prompt_trace.prompt_text == "Full prompt"
        assert prompt_trace.response_text == "Full response"
        assert prompt_trace.execution_time_ms == 150
        assert prompt_trace.token_count == 100


class TestEventLogModel:
    """Test EventLog model functionality."""

    async def test_eventlog_creation_with_required_fields(self, mem0_db_session: AsyncSession) -> None:
        """Test EventLog creation with required fields only."""
        base_log = BaseLog(level="INFO", message="Parent log")
        mem0_db_session.add(base_log)
        await mem0_db_session.flush()

        event_log = EventLog(base_log_id=base_log.id, event_type="user_action")
        mem0_db_session.add(event_log)
        await mem0_db_session.flush()

        # Verify fields
        assert event_log.id is not None
        assert isinstance(event_log.id, uuid.UUID)
        assert event_log.base_log_id == base_log.id
        assert event_log.event_type == "user_action"
        assert event_log.event_data is None  # Actual behavior: nullable
        assert event_log.created_at is not None

    async def test_eventlog_with_event_data(self, mem0_db_session: AsyncSession) -> None:
        """Test EventLog with JSONB event data."""
        base_log = BaseLog(level="INFO", message="Parent log")
        mem0_db_session.add(base_log)
        await mem0_db_session.flush()

        event_data = {"action": "click", "target": "button", "user_id": 123}
        event_log = EventLog(
            base_log_id=base_log.id,
            event_type="user_click",
            event_data=event_data,
            request_id=uuid.uuid4(),
        )
        mem0_db_session.add(event_log)
        await mem0_db_session.flush()

        assert event_log.event_data == event_data
        assert event_log.event_data["action"] == "click"
        assert event_log.request_id is not None


class TestModelBasicIntegration:
    """Test basic model integration scenarios."""

    async def test_cascade_delete_behavior(self, mem0_db_session: AsyncSession) -> None:
        """Test that child records are deleted when parent is deleted."""
        base_log = BaseLog(level="INFO", message="Parent log")
        mem0_db_session.add(base_log)
        await mem0_db_session.flush()

        # Create child records
        prompt_trace = PromptTrace(base_log_id=base_log.id, prompt_text="Test prompt")
        event_log = EventLog(base_log_id=base_log.id, event_type="test_event")
        mem0_db_session.add_all([prompt_trace, event_log])
        await mem0_db_session.flush()

        # Delete parent
        await mem0_db_session.delete(base_log)
        await mem0_db_session.commit()

        # Verify children are deleted (cascade)
        deleted_prompt = await mem0_db_session.get(PromptTrace, prompt_trace.id)
        deleted_event = await mem0_db_session.get(EventLog, event_log.id)
        assert deleted_prompt is None
        assert deleted_event is None
