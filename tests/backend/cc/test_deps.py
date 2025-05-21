"""Tests for the Control Center dependency injection functions.

This file contains unit tests for the dependency injection functions in the CC
module.
"""
# MDC: cc_module

import pytest

from src.backend.cc.deps import (
    get_db_session,
    get_module_config,
)


@pytest.mark.asyncio
async def test_get_module_config_structure() -> None:
    """Test get_module_config returns correct config structure.

    This test calls get_module_config and verifies that the returned dictionary
    has the expected keys and values.
    """
    config = await get_module_config()
    assert isinstance(config, dict)
    assert "version" in config
    assert "environment" in config
    assert config["version"] == "0.1.0"
    assert config["environment"] == "development"


@pytest.mark.asyncio
async def test_get_module_config_logs_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_module_config calls log_event.

    Monkeypatches log_event and checks that it is called when getting module config.
    """
    log_called: bool = False

    def fake_log_event(*args: object, **kwargs: object) -> None:
        nonlocal log_called
        log_called = True

    # Monkeypatch log_event used in deps.py by its full import path.
    monkeypatch.setattr(
        "src.backend.cc.deps.log_event",
        fake_log_event,
    )
    config = await get_module_config()
    assert log_called, "log_event was not called by get_module_config"
    assert isinstance(config, dict)
    assert config.get("version") == "0.1.0"
    assert config.get("environment") == "development"


@pytest.mark.asyncio
async def test_get_db_session_returns_mock() -> None:
    """Test that get_db_session returns a mock session.

    Calling get_db_session returns an async generator that yields a mock session.
    """
    session_gen = get_db_session()
    session = await anext(session_gen)
    assert session is not None
    # Verify it's a mock with AsyncSession interface
    assert hasattr(session, "execute")


@pytest.mark.asyncio
async def test_get_db_session_iteration_works() -> None:
    """Test async iteration over get_db_session yields a mock session.

    Calling the async generator and then iterating should yield exactly one value.
    """
    session_gen = get_db_session()
    count = 0
    async for session in session_gen:
        count += 1
        assert session is not None
    # Should yield exactly one session
    assert count == 1


@pytest.mark.asyncio
async def test_get_module_config_multiple_calls() -> None:
    """Test that multiple calls to get_module_config return consistent results."""
    config1 = await get_module_config()
    config2 = await get_module_config()
    assert config1 == config2
    assert config1["version"] == "0.1.0"
    assert config1["environment"] == "development"


@pytest.mark.asyncio
async def test_get_module_config_type_hints() -> None:
    """Test that get_module_config returns a dict with string keys and values."""
    config = await get_module_config()
    for key, value in config.items():
        assert isinstance(key, str)
        assert isinstance(value, str)
