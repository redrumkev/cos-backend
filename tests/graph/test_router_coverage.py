"""Additional tests for router.py to achieve 99.5%+ coverage.

Tests cover edge cases and error scenarios not covered in main test file.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.graph.base import get_async_neo4j
from src.graph.router import get_graph_service
from src.graph.router import router as graph_router


class TestGraphRouterCoverage:
    """Additional test cases for graph router coverage."""

    @pytest.fixture(scope="class")
    def app(self) -> Any:
        """Create test FastAPI app with graph router."""
        from tests.common.error_helpers import setup_error_handlers

        app = FastAPI()
        app.include_router(graph_router)
        setup_error_handlers(app)
        return app

    @pytest.fixture(scope="class")
    def client(self, app: Any) -> Any:
        """Create test client with mounted graph router."""
        return TestClient(app)

    @pytest.fixture
    def setup_mock_dependencies(self, app: Any) -> Any:
        """Set up mock dependencies for tests."""
        app.dependency_overrides.clear()
        yield
        app.dependency_overrides.clear()

    def test_health_check_exception(self, client: Any, app: Any) -> None:
        """Test health check with exception (lines 116-117)."""
        # Configure mock client to raise exception
        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.verify_connectivity.side_effect = Exception("Connection test failed")

        async def mock_get_client() -> AsyncIterator[AsyncMock]:
            yield mock_client

        app.dependency_overrides[get_async_neo4j] = mock_get_client

        response = client.get("/v1/graph/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["driver_type"] == "unknown"
        assert data["connected"] is False
        assert "Health check failed" in data["message"]

    def test_create_node_general_exception(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test node creation with general exception (lines 143-144)."""
        mock_service = AsyncMock()
        mock_service.create_node.side_effect = RuntimeError("Database connection lost")

        app.dependency_overrides[get_graph_service] = lambda: mock_service

        node_data = {"node_type": "Module", "module": "tech_cc", "properties": {"name": "test-node"}}
        response = client.post("/v1/graph/nodes", json=node_data)

        assert response.status_code == 500
        assert "Unable to create node in graph database" in response.json()["detail"]

    def test_get_node_general_exception(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test get node with general exception (lines 163-164)."""
        mock_service = AsyncMock()
        mock_service.get_node.side_effect = RuntimeError("Query timeout")

        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/nodes/Module/tech_cc/test-id")

        assert response.status_code == 500
        assert "Unable to retrieve node from graph database" in response.json()["detail"]

    def test_update_node_not_found(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test update node when node not found (line 179)."""
        mock_service = AsyncMock()
        mock_service.update_node.return_value = None

        app.dependency_overrides[get_graph_service] = lambda: mock_service

        update_data = {"properties": {"name": "updated-node"}}
        response = client.put("/v1/graph/nodes/Module/tech_cc/nonexistent", json=update_data)

        assert response.status_code == 404
        assert "Node nonexistent not found in graph" in response.json()["detail"]

    def test_update_node_general_exception(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test update node with general exception (lines 184-185)."""
        mock_service = AsyncMock()
        mock_service.update_node.side_effect = RuntimeError("Update failed")

        app.dependency_overrides[get_graph_service] = lambda: mock_service

        update_data = {"properties": {"name": "updated-node"}}
        response = client.put("/v1/graph/nodes/Module/tech_cc/test-id", json=update_data)

        assert response.status_code == 500
        assert "Unable to update node in graph database" in response.json()["detail"]

    def test_delete_node_not_found(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test delete node when node not found (line 200)."""
        mock_service = AsyncMock()
        mock_service.delete_node.return_value = False

        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.delete("/v1/graph/nodes/Module/tech_cc/nonexistent")

        assert response.status_code == 404
        assert "Node nonexistent not found in graph" in response.json()["detail"]

    def test_delete_node_general_exception(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test delete node with general exception (lines 205-206)."""
        mock_service = AsyncMock()
        mock_service.delete_node.side_effect = RuntimeError("Delete failed")

        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.delete("/v1/graph/nodes/Module/tech_cc/test-id")

        assert response.status_code == 500
        assert "Unable to delete node from graph database" in response.json()["detail"]

    def test_get_nodes_by_property_exception(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test get nodes by property with exception (lines 224-225)."""
        mock_service = AsyncMock()
        mock_service.get_nodes_by_property.side_effect = RuntimeError("Query failed")

        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/nodes/Module/tech_cc?property_name=name&property_value=test")

        assert response.status_code == 500
        assert "Unable to search nodes by property" in response.json()["detail"]

    def test_search_nodes_exception(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test search nodes with exception (lines 242-243)."""
        mock_service = AsyncMock()
        mock_service.search_nodes.side_effect = RuntimeError("Search failed")

        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/search?search_text=test")

        assert response.status_code == 500
        assert "Unable to search nodes in graph database" in response.json()["detail"]

    def test_create_relationship_exception(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test create relationship with exception (lines 266-267)."""
        mock_service = AsyncMock()
        mock_service.create_relationship.side_effect = RuntimeError("Relationship creation failed")

        app.dependency_overrides[get_graph_service] = lambda: mock_service

        rel_data = {
            "relationship_type": "CONTAINS",
            "from_node_type": "Module",
            "from_module": "tech_cc",
            "from_node_id": "node-1",
            "to_node_type": "Module",
            "to_module": "tech_cc",
            "to_node_id": "node-2",
        }
        response = client.post("/v1/graph/relationships", json=rel_data)

        assert response.status_code == 500
        assert "Unable to create relationship in graph database" in response.json()["detail"]

    def test_get_node_relationships_exception(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test get node relationships with exception (lines 283-284)."""
        mock_service = AsyncMock()
        mock_service.get_node_relationships.side_effect = RuntimeError("Relationships query failed")

        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/nodes/Module/tech_cc/node-1/relationships")

        assert response.status_code == 500
        assert "Unable to retrieve node relationships from graph database" in response.json()["detail"]

    def test_get_schema_info(self, client: Any) -> None:
        """Test get schema info endpoint (lines 291-293)."""
        response = client.get("/v1/graph/schema")

        assert response.status_code == 200
        data = response.json()

        # Check that schema info is returned
        assert "node_types" in data
        assert "modules" in data  # The actual response has 'modules', not 'module_labels'
        assert "relationship_types" in data

        # Verify structure
        assert isinstance(data["node_types"], list)
        assert isinstance(data["modules"], list)
        assert isinstance(data["relationship_types"], list)

    def test_health_check_with_rust_driver(self, client: Any, app: Any) -> None:
        """Test health check detecting rust driver type."""
        mock_client = AsyncMock()
        mock_client.is_connected = True

        # Create a custom class with 'rust' in its name
        class RustAsyncDriver:
            pass

        # Create an instance of our rust driver
        mock_driver = RustAsyncDriver()
        mock_client.driver = mock_driver
        mock_client.verify_connectivity.return_value = True

        async def mock_get_client() -> AsyncIterator[AsyncMock]:
            yield mock_client

        app.dependency_overrides[get_async_neo4j] = mock_get_client

        response = client.get("/v1/graph/health")

        assert response.status_code == 200
        data = response.json()
        # The logic checks if "rust" in str(type(client.driver)).lower()
        # For our mock, str(type(driver)) would be something like "<class 'test_router_coverage.RustAsyncDriver'>"
        # which contains 'rust' in lowercase
        assert data["driver_type"] == "rust"

    def test_get_stats_service_exception(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test stats endpoint when service raises exception."""
        mock_service = AsyncMock()
        mock_service.get_graph_stats.side_effect = RuntimeError("Stats calculation failed")

        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/stats")

        assert response.status_code == 500
        assert "Unable to retrieve graph statistics" in response.json()["detail"]

    def test_get_node_relationships_with_filters(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test get node relationships with all filter options."""
        mock_service = AsyncMock()
        mock_service.get_node_relationships.return_value = [
            {"type": "CONTAINS", "related_node": "node-2"},
            {"type": "REFERENCES", "related_node": "node-3"},
        ]

        app.dependency_overrides[get_graph_service] = lambda: mock_service

        # Test with relationship type filter
        response = client.get(
            "/v1/graph/nodes/Module/tech_cc/node-1/relationships?direction=out&relationship_type=CONTAINS"
        )

        assert response.status_code == 200

        # Verify service was called with correct parameters
        mock_service.get_node_relationships.assert_called_with("node-1", "Module", "tech_cc", "out", "CONTAINS")
