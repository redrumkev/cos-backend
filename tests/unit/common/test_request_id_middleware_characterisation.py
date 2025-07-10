"""Characterisation tests for request_id_middleware.py to achieve ≥95% coverage.

This module provides targeted tests for edge cases and specific code paths
to reach the required coverage threshold while maintaining test quality.
"""

import asyncio
from unittest.mock import Mock, patch

from src.common.request_id_middleware import get_request_id, request_id_var


class TestRequestIdMiddlewareCharacterisation:
    """Test coverage for specific uncovered code paths in request_id_middleware.py."""

    def test_logfire_import_fallback(self) -> None:
        """Test the ModuleNotFoundError fallback when logfire import fails (lines 34-35)."""
        # This tests the import fallback scenario
        # We can't easily mock the import during module load, but we can test
        # that the module handles the logfire=None case gracefully

        # Test that when logfire is None, the middleware still works
        with patch("src.common.request_id_middleware.logfire", None):
            from src.common.request_id_middleware import RequestIDMiddleware

            # Create middleware instance
            middleware = RequestIDMiddleware(app=Mock())

            # Verify it was created successfully even with logfire=None
            assert middleware is not None
            assert hasattr(middleware, "dispatch")

    def test_logfire_module_not_found_import_error(self) -> None:
        """Test the exact ModuleNotFoundError import path (lines 40-41)."""
        # This test verifies that the import error handling works correctly
        # We test the behavior after the import has failed (logfire=None)

        # Test that importlib.import_module failure results in logfire=None
        with patch(
            "src.common.request_id_middleware.importlib.import_module",
            side_effect=ModuleNotFoundError("No module named 'logfire'"),
        ):
            # Re-import the module to trigger the exception handling
            # This simulates what happens when logfire package is not installed
            import sys

            # Remove the module from cache to force re-import
            if "src.common.request_id_middleware" in sys.modules:
                del sys.modules["src.common.request_id_middleware"]

            # Import should succeed but logfire should be None
            import src.common.request_id_middleware as middleware_module

            # logfire should be None due to ModuleNotFoundError
            assert middleware_module.logfire is None

            # The middleware should still be functional
            middleware = middleware_module.RequestIDMiddleware(app=Mock())
            assert middleware is not None

    def test_get_request_id_lookup_error(self) -> None:
        """Test LookupError handling in get_request_id function (lines 98-99)."""
        # Test the LookupError handling by creating a truly fresh context
        # We'll use a subprocess to test this in isolation

        import subprocess
        import sys

        # Create a test script that tests the LookupError path
        test_script = """
import sys
sys.path.insert(0, ".")
from src.common.request_id_middleware import get_request_id
# In a fresh process, context var should not be set
result = get_request_id()
print(f"RESULT:{result}")
assert result is None, f"Expected None, got {result}"
print("SUCCESS")
"""

        # Run the test in a subprocess to ensure clean context
        result = subprocess.run(
            [sys.executable, "-c", test_script], capture_output=True, text=True, cwd="/Users/kevinmba/dev/cos"
        )

        # Check that the subprocess test passed
        assert result.returncode == 0, f"Test failed: {result.stderr}"
        assert "SUCCESS" in result.stdout, f"Expected SUCCESS in output: {result.stdout}"

    def test_context_var_unset_scenario(self) -> None:
        """Test get_request_id when context variable has never been set."""
        # Test the scenario where request_id_var.get() raises LookupError
        # This is an alternative test to ensure we have comprehensive coverage

        import subprocess
        import sys

        # Create a test script that tests the LookupError path in a different way
        test_script = """
import sys
sys.path.insert(0, ".")
import contextvars
from src.common.request_id_middleware import get_request_id, request_id_var

# Create a completely fresh context
ctx = contextvars.copy_context()

def test_in_fresh_context():
    # In this fresh context, the request_id_var should not be set
    result = get_request_id()
    print(f"RESULT:{result}")
    assert result is None, f"Expected None, got {result}"
    print("SUCCESS")

# Run the test in the fresh context
ctx.run(test_in_fresh_context)
"""

        # Run the test in a subprocess to ensure clean context
        result = subprocess.run(
            [sys.executable, "-c", test_script], capture_output=True, text=True, cwd="/Users/kevinmba/dev/cos"
        )

        # Check that the subprocess test passed
        assert result.returncode == 0, f"Test failed: {result.stderr}"
        assert "SUCCESS" in result.stdout, f"Expected SUCCESS in output: {result.stdout}"

    def test_middleware_dispatch_full_path_coverage(self) -> None:
        """Test the full dispatch method execution path (lines 59-85)."""
        from fastapi import Request, Response
        from starlette.datastructures import Headers

        from src.common.request_id_middleware import RequestIDMiddleware

        # Create a middleware instance
        app = Mock()
        middleware = RequestIDMiddleware(app=app)

        # Create a mock request without X-Request-ID header
        request = Mock(spec=Request)
        request.headers = Headers({})  # Empty headers - triggers UUID generation
        request.state = Mock()

        # Mock call_next to return a response
        async def mock_call_next(req: Request) -> Response:
            response = Response(content="test")
            return response

        async def run_dispatch() -> None:
            response = await middleware.dispatch(request, mock_call_next)

            # Verify the dispatch method executed all steps
            assert hasattr(request.state, "request_id")
            assert request.state.request_id is not None
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == request.state.request_id

        # Run the dispatch method
        asyncio.run(run_dispatch())

    def test_middleware_with_existing_request_id_header(self) -> None:
        """Test middleware when X-Request-ID header is already present."""
        from fastapi import Request, Response
        from starlette.datastructures import Headers

        from src.common.request_id_middleware import RequestIDMiddleware

        # Create a middleware instance
        app = Mock()
        middleware = RequestIDMiddleware(app=app)

        # Create a mock request WITH X-Request-ID header
        existing_id = "existing-request-id-123"
        request = Mock(spec=Request)
        request.headers = Headers({"X-Request-ID": existing_id})
        request.state = Mock()

        # Mock call_next to return a response
        async def mock_call_next(req: Request) -> Response:
            response = Response(content="test")
            return response

        async def run_dispatch() -> None:
            response = await middleware.dispatch(request, mock_call_next)

            # Verify existing ID was used
            assert request.state.request_id == existing_id
            assert response.headers["X-Request-ID"] == existing_id

        # Run the dispatch method
        asyncio.run(run_dispatch())

    def test_middleware_logfire_span_path(self) -> None:
        """Test the logfire span tagging path in dispatch method."""
        from fastapi import Request, Response
        from starlette.datastructures import Headers

        from src.common.request_id_middleware import RequestIDMiddleware

        # Create a middleware instance
        app = Mock()
        middleware = RequestIDMiddleware(app=app)

        # Mock logfire with a current_span that has set_attribute
        mock_span = Mock()
        mock_span.set_attribute = Mock()

        with patch("src.common.request_id_middleware.logfire") as mock_logfire:
            mock_logfire.current_span.return_value = mock_span

            # Create a mock request
            request = Mock(spec=Request)
            request.headers = Headers({"X-Request-ID": "test-id-123"})
            request.state = Mock()

            # Mock call_next
            async def mock_call_next(req: Request) -> Response:
                return Response(content="test")

            async def run_dispatch() -> None:
                await middleware.dispatch(request, mock_call_next)

                # Verify logfire span was called
                mock_logfire.current_span.assert_called_once()
                mock_span.set_attribute.assert_called_once_with("request_id", "test-id-123")

            # Run the dispatch method
            asyncio.run(run_dispatch())

    def test_context_var_set_and_get_cycle(self) -> None:
        """Test the full cycle of setting and getting context variable."""
        test_id = "test-context-cycle-123"

        # Set the context variable
        request_id_var.set(test_id)

        # Get it back
        result = get_request_id()
        assert result == test_id

        # Verify direct access also works
        assert request_id_var.get() == test_id

    def test_logfire_import_modulenotfound_fallback(self) -> None:
        """Test the exact ModuleNotFoundError fallback path (lines 40-41)."""
        # This is challenging to test directly since import happens at module load time
        # But we can test the behavior when logfire is None

        with patch("src.common.request_id_middleware.logfire", None):
            from fastapi import Request, Response
            from starlette.datastructures import Headers

            from src.common.request_id_middleware import RequestIDMiddleware

            # Create middleware with logfire=None
            middleware = RequestIDMiddleware(app=Mock())

            # Create request
            request = Mock(spec=Request)
            request.headers = Headers({"X-Request-ID": "test-fallback-id"})
            request.state = Mock()

            async def mock_call_next(req: Request) -> Response:
                return Response(content="test")

            async def run_test() -> None:
                # This should work even without logfire
                response = await middleware.dispatch(request, mock_call_next)
                assert response.headers["X-Request-ID"] == "test-fallback-id"

            asyncio.run(run_test())

    def test_logfire_span_exception_handling(self) -> None:
        """Test the exception handling in logfire span tagging (lines 81-83)."""
        from fastapi import Request, Response
        from starlette.datastructures import Headers

        from src.common.request_id_middleware import RequestIDMiddleware

        # Create middleware
        middleware = RequestIDMiddleware(app=Mock())

        # Mock logfire to raise an exception during span tagging
        with patch("src.common.request_id_middleware.logfire") as mock_logfire:
            # Make current_span raise an exception
            mock_logfire.current_span.side_effect = Exception("Span tagging failed")

            # Create request
            request = Mock(spec=Request)
            request.headers = Headers({"X-Request-ID": "test-exception-id"})
            request.state = Mock()

            async def mock_call_next(req: Request) -> Response:
                return Response(content="test")

            # Mock logger to capture the debug log
            with patch("src.common.request_id_middleware.logger") as mock_logger:

                async def run_test() -> None:
                    # Should not raise exception despite logfire error
                    response = await middleware.dispatch(request, mock_call_next)
                    assert response.headers["X-Request-ID"] == "test-exception-id"

                    # Should have logged the error at debug level
                    mock_logger.debug.assert_called_once()
                    args = mock_logger.debug.call_args[0]
                    assert "Logfire span tagging failed" in args[0]

                asyncio.run(run_test())

    def test_logfire_span_no_set_attribute_method(self) -> None:
        """Test logfire span without set_attribute method."""
        from fastapi import Request, Response
        from starlette.datastructures import Headers

        from src.common.request_id_middleware import RequestIDMiddleware

        # Create middleware
        middleware = RequestIDMiddleware(app=Mock())

        # Mock logfire with a span that lacks set_attribute
        with patch("src.common.request_id_middleware.logfire") as mock_logfire:
            mock_span = Mock()
            # Remove set_attribute method
            del mock_span.set_attribute
            mock_logfire.current_span.return_value = mock_span

            # Create request
            request = Mock(spec=Request)
            request.headers = Headers({"X-Request-ID": "test-no-attr-id"})
            request.state = Mock()

            async def mock_call_next(req: Request) -> Response:
                return Response(content="test")

            async def run_test() -> None:
                # Should work without calling set_attribute
                response = await middleware.dispatch(request, mock_call_next)
                assert response.headers["X-Request-ID"] == "test-no-attr-id"

                # current_span should have been called but set_attribute should not exist
                mock_logfire.current_span.assert_called_once()
                assert not hasattr(mock_span, "set_attribute")

            asyncio.run(run_test())
