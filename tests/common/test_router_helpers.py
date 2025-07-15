"""Tests for router path mapping helpers."""

import pytest

from tests.common.router_helpers import (
    TEST_ENDPOINT_MAPPINGS,
    get_debug_endpoint_path,
    get_module_resource_path,
    get_test_endpoint_path,
    get_versioned_endpoint_path,
)


class TestRouterHelpers:
    """Test cases for router path mapping helpers."""

    def test_get_test_endpoint_path_cc_module(self) -> None:
        """Test endpoint path mapping for CC module."""
        assert get_test_endpoint_path("health", "cc") == "/cc/health"
        assert get_test_endpoint_path("modules", "cc") == "/cc/modules"
        assert get_test_endpoint_path("debug", "cc") == "/cc/debug"
        assert get_test_endpoint_path("config", "cc") == "/cc/config"
        assert get_test_endpoint_path("status", "cc") == "/cc/status"
        assert get_test_endpoint_path("mem0", "cc") == "/cc/mem0"

    def test_get_test_endpoint_path_graph_module(self) -> None:
        """Test endpoint path mapping for Graph module."""
        assert get_test_endpoint_path("health", "graph") == "/graph/health"
        assert get_test_endpoint_path("nodes", "graph") == "/graph/nodes"
        assert get_test_endpoint_path("relationships", "graph") == "/graph/relationships"

    def test_get_test_endpoint_path_unknown_endpoint(self) -> None:
        """Test endpoint path mapping for unknown endpoints."""
        assert get_test_endpoint_path("unknown", "cc") == "/cc/unknown"
        assert get_test_endpoint_path("unknown", "graph") == "/graph/unknown"

    def test_get_test_endpoint_path_unsupported_module(self) -> None:
        """Test endpoint path mapping for unsupported modules."""
        with pytest.raises(ValueError, match="Unsupported module: unknown"):
            get_test_endpoint_path("health", "unknown")

    def test_get_versioned_endpoint_path_default_version(self) -> None:
        """Test versioned endpoint path with default version."""
        assert get_versioned_endpoint_path("health", "cc") == "/v1/cc/health"
        assert get_versioned_endpoint_path("modules", "cc") == "/v1/cc/modules"

    def test_get_versioned_endpoint_path_custom_version(self) -> None:
        """Test versioned endpoint path with custom version."""
        assert get_versioned_endpoint_path("health", "cc", "v2") == "/v2/cc/health"
        assert get_versioned_endpoint_path("nodes", "graph", "v2") == "/v2/graph/nodes"

    def test_get_module_resource_path_cc(self) -> None:
        """Test module resource path for CC module."""
        resource_id = "123e4567-e89b-12d3-a456-426614174000"
        expected = "/v1/cc/modules/123e4567-e89b-12d3-a456-426614174000"
        assert get_module_resource_path(resource_id, "cc") == expected

    def test_get_module_resource_path_graph(self) -> None:
        """Test module resource path for Graph module."""
        resource_id = "test-node-id"
        expected = "/v1/graph/modules/test-node-id"
        assert get_module_resource_path(resource_id, "graph") == expected

    def test_get_debug_endpoint_path_cc(self) -> None:
        """Test debug endpoint path for CC module."""
        assert get_debug_endpoint_path("log", "cc") == "/cc/debug/log"
        assert get_debug_endpoint_path("redis-health", "cc") == "/cc/debug/redis-health"

    def test_get_debug_endpoint_path_graph(self) -> None:
        """Test debug endpoint path for Graph module."""
        assert get_debug_endpoint_path("log", "graph") == "/graph/debug/log"

    def test_convenience_mappings_cc_endpoints(self) -> None:
        """Test convenience mappings for CC endpoints."""
        assert TEST_ENDPOINT_MAPPINGS["cc_health"] == "/cc/health"
        assert TEST_ENDPOINT_MAPPINGS["cc_modules"] == "/cc/modules"
        assert TEST_ENDPOINT_MAPPINGS["cc_debug_log"] == "/cc/debug/log"
        assert TEST_ENDPOINT_MAPPINGS["cc_debug_redis"] == "/cc/debug/redis-health"

    def test_convenience_mappings_versioned_cc_endpoints(self) -> None:
        """Test convenience mappings for versioned CC endpoints."""
        assert TEST_ENDPOINT_MAPPINGS["v1_cc_health"] == "/v1/cc/health"
        assert TEST_ENDPOINT_MAPPINGS["v1_cc_modules"] == "/v1/cc/modules"
        assert TEST_ENDPOINT_MAPPINGS["v1_cc_debug_log"] == "/v1/cc/debug/log"

    def test_convenience_mappings_graph_endpoints(self) -> None:
        """Test convenience mappings for Graph endpoints."""
        assert TEST_ENDPOINT_MAPPINGS["graph_health"] == "/graph/health"
        assert TEST_ENDPOINT_MAPPINGS["graph_nodes"] == "/graph/nodes"
        assert TEST_ENDPOINT_MAPPINGS["graph_relationships"] == "/graph/relationships"

    def test_convenience_mappings_versioned_graph_endpoints(self) -> None:
        """Test convenience mappings for versioned Graph endpoints."""
        assert TEST_ENDPOINT_MAPPINGS["v1_graph_health"] == "/v1/graph/health"
        assert TEST_ENDPOINT_MAPPINGS["v1_graph_nodes"] == "/v1/graph/nodes"
        assert TEST_ENDPOINT_MAPPINGS["v1_graph_relationships"] == "/v1/graph/relationships"


class TestRouterHelpersIntegration:
    """Integration tests for router helpers with real endpoint patterns."""

    def test_cc_module_endpoint_patterns(self) -> None:
        """Test that CC module endpoints follow expected patterns."""
        # Test non-versioned endpoints
        health_path = get_test_endpoint_path("health", "cc")
        assert health_path.startswith("/cc/")
        assert "health" in health_path

        # Test versioned endpoints
        versioned_health = get_versioned_endpoint_path("health", "cc", "v1")
        assert versioned_health.startswith("/v1/cc/")
        assert "health" in versioned_health

    def test_graph_module_endpoint_patterns(self) -> None:
        """Test that Graph module endpoints follow expected patterns."""
        # Test non-versioned endpoints
        nodes_path = get_test_endpoint_path("nodes", "graph")
        assert nodes_path.startswith("/graph/")
        assert "nodes" in nodes_path

        # Test versioned endpoints
        versioned_nodes = get_versioned_endpoint_path("nodes", "graph", "v1")
        assert versioned_nodes.startswith("/v1/graph/")
        assert "nodes" in versioned_nodes

    def test_resource_id_patterns(self) -> None:
        """Test resource ID patterns work correctly."""
        # Test UUID pattern
        uuid_id = "123e4567-e89b-12d3-a456-426614174000"
        uuid_path = get_module_resource_path(uuid_id, "cc")
        assert uuid_id in uuid_path
        assert uuid_path.endswith(uuid_id)

        # Test simple ID pattern
        simple_id = "test-123"
        simple_path = get_module_resource_path(simple_id, "cc")
        assert simple_id in simple_path
        assert simple_path.endswith(simple_id)

    def test_debug_endpoint_patterns(self) -> None:
        """Test debug endpoint patterns work correctly."""
        log_path = get_debug_endpoint_path("log", "cc")
        assert "/debug/" in log_path
        assert log_path.endswith("log")

        redis_path = get_debug_endpoint_path("redis-health", "cc")
        assert "/debug/" in redis_path
        assert redis_path.endswith("redis-health")
