# ruff: noqa: E402
import functools
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add these type definitions to help with decorator typing
T = TypeVar("T", bound=Callable[..., Any])


# Use a properly typed decorator pattern that passes through fixture arguments
def fixture_wrapper(
    scope: str | None = None, **fixture_kwargs: Any
) -> Callable[[T], T]:
    """Being wrapper to preserve types for pytest fixtures."""

    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        fixture_kwargs_with_scope = fixture_kwargs
        if scope:
            fixture_kwargs_with_scope["scope"] = scope

        return pytest.fixture(**fixture_kwargs_with_scope)(wrapper)  # type: ignore

    return decorator


project_root = Path(__file__).parent.parent  # Should be g:\cos
src_path = project_root / "src"  # Should be g:\cos\src
# Add src_path first so its packages (backend, common) are preferred
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
# Add project_root if needed for finding cos_main directly
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# Import the app AFTER potentially modifying sys.path
from cos_main import app as cos_app  # Rename the import

# Cast the imported app to FastAPI type
main_app = cast(FastAPI, cos_app)


@fixture_wrapper(scope="session")
def app() -> FastAPI:
    """Create main FastAPI application instance for testing.

    Scope is 'session' if the app state is safe to share across all tests.
    Use 'function' scope if tests modify app state (e.g., dependencies).
    """
    return main_app


@fixture_wrapper(scope="function")
def test_client(app: FastAPI) -> TestClient:
    """Creates a TestClient for making requests to the test app.

    Scope is 'function' to ensure isolation between tests.
    """
    return TestClient(app)
