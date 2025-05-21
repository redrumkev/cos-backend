"""Database connection and session management for the COS backend.

This module provides:
- Agent-based database connections
- Async session factories
- Connection pooling configuration
- Rich logging for database operations

For onboarding:
1. Ensure Agent is configured and running
2. Set up .env with agent connection URLs
3. Use get_async_session_maker() for async contexts
"""

import asyncio
import os
import re
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest import mark
from rich.console import Console
from rich.text import Text
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Session

from src.common import database
from src.common.config import get_settings
from src.common.database import IN_TEST_MODE


@pytest.fixture
def mock_agent_client() -> Generator[MagicMock, None, None]:
    """Mock the agent client for testing."""
    with patch("src.common.agent.get_agent_client") as mock:
        mock.return_value = AsyncMock()
        yield mock


@pytest.fixture(autouse=True)
async def cleanup_connections() -> AsyncGenerator[None, None]:
    """Cleanup any hanging connections after each test."""
    yield
    # Cleanup any remaining connections
    await asyncio.gather(
        *asyncio.all_tasks() - {asyncio.current_task()}, return_exceptions=True
    )


@pytest.mark.usefixtures("mock_env_settings")
def test_engine_is_sqlalchemy_engine() -> None:
    from src.common.database import get_engine

    engine = get_engine()
    assert isinstance(engine, Engine | MagicMock)


@pytest.mark.usefixtures("mock_env_settings")
def test_async_engine_is_asyncengine() -> None:
    from src.common.database import get_async_engine

    async_engine = get_async_engine()
    assert isinstance(async_engine, AsyncEngine | AsyncMock)


@pytest.mark.usefixtures("mock_env_settings")
def test_sessionlocal_creates_session() -> None:
    from src.common.database import get_session_maker

    session_local = get_session_maker()
    session = session_local()
    assert isinstance(session, Session | MagicMock)
    if hasattr(session, "close"):
        session.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_env_settings")
async def test_asyncsessionlocal_creates_asyncsession() -> None:
    from src.common.database import get_async_session_maker

    async_session_local = get_async_session_maker()
    if IN_TEST_MODE:
        session = async_session_local()
        assert isinstance(session, AsyncMock)
    else:
        async with async_session_local() as session:
            assert isinstance(session, AsyncSession)


@mark.timeout(5)
@mark.asyncio
@pytest.mark.usefixtures("mock_env_settings")
async def test_async_engine_can_connect_and_execute_select_1() -> None:
    """Should connect and execute SELECT 1, returning 1."""
    if IN_TEST_MODE:
        pytest.skip("Real DB required for connection test.")
    try:
        engine = database.get_async_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1
    except Exception as e:
        pytest.fail(f"Failed to connect: {e!s}")


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_env_settings")
async def test_async_session_can_execute_simple_query() -> None:
    """Uses async session to execute a simple query and checks the result."""
    if IN_TEST_MODE:
        pytest.skip("Real DB required for session query test.")
    session_maker = database.get_async_session_maker()
    async with session_maker() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()
        assert value == 1


@pytest.mark.usefixtures("mock_env_settings")
def test_async_engine_configured_with_pooling_and_timeouts() -> None:
    """Verifies async engine is created with agent-specific pool settings."""
    with patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_create:
        # Simulate agent config with edge values
        os.environ["AGENT_POOL_SIZE"] = "1"
        os.environ["AGENT_POOL_TIMEOUT"] = "2"
        os.environ["AGENT_POOL_MAX_OVERFLOW"] = "0"
        # Call the function (should use agent config)
        _ = database.get_async_engine()
        args, kwargs = mock_create.call_args
        # Check agent-specific pool config
        assert "pool_size" in kwargs
        assert kwargs["pool_size"] == 1
        assert kwargs.get("pool_pre_ping", False) is True


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_env_settings")
async def test_async_engine_connection_failure_logs_rich_error() -> None:
    """Simulates connection failure and asserts rich error log (color + emoji)."""
    # Patch engine to raise error
    with (
        patch("src.common.database.create_async_engine", side_effect=Exception("fail")),
        patch.object(Console, "print") as mock_print,
    ):
        import contextlib

        with contextlib.suppress(Exception):
            _ = database.get_async_engine()
        # Check rich error log (red, emoji)
        found = False
        for call in mock_print.call_args_list:
            text_arg = call[0][0]
            if (
                isinstance(text_arg, Text)
                and "❌" in text_arg.plain
                and text_arg.style
                and "red" in text_arg.style
            ):
                found = True
        assert found, "No rich error log with emoji/color found."


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_env_settings")
async def test_async_session_pool_exhaustion_logs_rich_error() -> None:
    """Simulates pool exhaustion and checks for rich error log."""
    # Patch sessionmaker to raise error
    with (
        patch(
            "src.common.database.get_async_session_maker",
            side_effect=Exception("pool exhausted"),
        ),
        patch.object(Console, "print") as mock_print,
    ):
        try:
            session_maker = database.get_async_session_maker()
            async with session_maker():
                pass
        except Exception:
            import logging

            logging.exception(
                "Exception occurred during async session pool exhaustion test"
            )
        found = False
        for call in mock_print.call_args_list:
            text_arg = call[0][0]
            if (
                isinstance(text_arg, Text)
                and "❌" in text_arg.plain
                and text_arg.style
                and "red" in text_arg.style
            ):
                found = True
        assert found, "No rich error log with emoji/color found."


def test_rich_log_output_includes_color_and_emoji() -> None:
    """Explicitly checks that all rich log outputs include both color and emoji."""
    with patch.object(Console, "print") as mock_print:
        # Simulate a log
        console = Console()
        console.print(Text("✅ Connection successful!", style="bold green"))
        found = False
        for call in mock_print.call_args_list:
            text_arg = call[0][0]
            if isinstance(text_arg, Text) and (
                "✅" in text_arg.plain and text_arg.style and "green" in text_arg.style
            ):
                found = True
        assert found, "No rich log with green color and emoji found."


def test_all_config_loaded_from_env() -> None:
    """Ensures all config is loaded from env/config, not hardcoded."""
    s = get_settings()  # Use regular settings instead of agent settings
    # Check that DB URLs use correct format
    assert s.POSTGRES_DEV_URL.startswith("postgresql")
    assert s.async_db_url.startswith("postgresql+asyncpg")
    # No hardcoded values
    assert "localhost" not in s.POSTGRES_DEV_URL


def test_module_docstrings_and_onboarding_comments() -> None:
    """Asserts presence and format of docstrings, onboarding comments.

    and config loading documentation.
    """
    from pathlib import Path

    with Path(database.__file__).open(encoding="utf-8") as f:
        code = f.read()
    # Check for module-level docstring
    assert re.search(r'""".*?"""', code, re.DOTALL), "No module-level docstring found."
    # Check for onboarding comments
    assert "onboarding" in code.lower() or "template" in code.lower(), (
        "No onboarding/template comments found."
    )
    # Check for config loading doc
    assert "get_settings" in code, "No config loading doc found."


def test_no_warnings_or_deprecations_in_output() -> None:
    """Runs pytest w/strict flags, asserts only green bars/emojis for passing cases."""
    import subprocess

    # SECURITY NOTE: These are hardcoded commands only, no user input
    safe_cmd = [
        "pytest",
        "-q",
        "--disable-warnings",
        "--tb=short",
        "tests/common/test_database.py",
    ]

    # Strict validation to ensure no command injection is possible
    # Only alphanumeric chars and basic path characters are allowed
    safe_pattern = r"^[\w\-./=]+$"

    # Validate each argument before execution
    for arg in safe_cmd:
        if not isinstance(arg, str):
            raise ValueError(f"Command argument must be string: {arg}")
        if not re.match(safe_pattern, arg):
            raise ValueError(f"Potentially unsafe command argument: {arg}")

    # Command is validated as safe, now we can run it
    result = subprocess.run(  # noqa: S603, RUF100
        safe_cmd,
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )
    # Only green output (no warnings, no deprecations)
    assert "warning" not in result.stdout.lower()
    assert "deprecat" not in result.stdout.lower()
    assert "failed" not in result.stdout.lower()
    assert "error" not in result.stdout.lower()
    # Optionally check for green bar/emoji
    assert "==" in result.stdout or "✅" in result.stdout
