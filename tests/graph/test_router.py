"""Tests for graph router endpoints."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest  # Phase 2: Remove for skip removal
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.graph.base import get_async_neo4j
from src.graph.router import router as graph_router

# Phase 2: Skip block removed for Neo4j client implementation (P2-GRAPH-001 completed)


class TestGraphRouter:
    """Test cases for graph router endpoints."""

    @pytest.fixture(scope="class")
    def app(self) -> Any:
        """Create test FastAPI app with graph router."""
        app = FastAPI()
        # Don't add another /graph prefix since the router already has one
        app.include_router(graph_router)
        return app

    @pytest.fixture(scope="class")
    def client(self, app: Any) -> Any:
        """Create test client with mounted graph router."""
        return TestClient(app)

    @pytest.fixture
    def setup_mock_dependencies(self, app: Any) -> Any:
        """Set up mock dependencies for tests."""
        # Clear any existing overrides
        app.dependency_overrides.clear()
        yield
        # Clean up after test
        app.dependency_overrides.clear()

    def test_health_check_success(self, client: Any, app: Any) -> None:
        """Test successful health check endpoint."""
        # Configure mock client for health check
        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.driver = MagicMock()  # Mock driver for type detection
        mock_client.verify_connectivity.return_value = True

        # Create an async generator that yields the mock client
        async def mock_get_client():  # type: ignore[no-untyped-def]
            yield mock_client

        # Override the dependency
        app.dependency_overrides[get_async_neo4j] = mock_get_client

        response = client.get("/v1/graph/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["connected"] is True

    def test_health_check_failure(self, client: Any, app: Any) -> None:
        """Test health check failure endpoint."""
        # Configure mock client for health check failure
        mock_client = AsyncMock()
        mock_client.is_connected = False
        mock_client.driver = MagicMock()  # Mock driver for type detection
        mock_client.verify_connectivity.return_value = False

        # Create an async generator that yields the mock client
        async def mock_get_client():  # type: ignore[no-untyped-def]
            yield mock_client

        # Override the dependency
        app.dependency_overrides[get_async_neo4j] = mock_get_client

        response = client.get("/v1/graph/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["connected"] is False

    def test_get_stats_success(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test successful stats retrieval endpoint."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.get_graph_stats.return_value = {
            "total_nodes": 100,
            "total_relationships": 50,
            "node_types": {"Module": 10, "Prompt": 90},
        }

        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_nodes"] == 100

    def test_create_node_success(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test successful node creation endpoint."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.create_node.return_value = {
            "id": "test-id",
            "labels": ["Module", "tech_cc"],
            "properties": {"name": "test-node"},
        }
        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        node_data = {"node_type": "Module", "module": "tech_cc", "properties": {"name": "test-node"}}
        response = client.post("/v1/graph/nodes", json=node_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "test-id"

    def test_create_node_validation_error(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test node creation with validation error."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.create_node.side_effect = ValueError("Invalid node structure")

        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        node_data = {"node_type": "Module", "module": "tech_cc", "properties": {"name": "test-node"}}
        response = client.post("/v1/graph/nodes", json=node_data)

        assert response.status_code == 400

    def test_get_node_success(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test successful node retrieval endpoint."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.get_node.return_value = {
            "id": "test-id",
            "labels": ["Module", "tech_cc"],
            "properties": {"name": "test-node"},
        }
        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/nodes/Module/tech_cc/test-id")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "test-id"

    def test_get_node_not_found(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test getting a node that doesn't exist."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.get_node.return_value = None
        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/nodes/Module/tech_cc/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_node_success(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test successful node update endpoint."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.update_node.return_value = {"updated": True}
        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        update_data = {"properties": {"name": "updated-node"}}
        response = client.put("/v1/graph/nodes/Module/tech_cc/test-id", json=update_data)

        assert response.status_code == 200

    def test_delete_node_success(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test successful node deletion endpoint."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.delete_node.return_value = True
        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.delete("/v1/graph/nodes/Module/tech_cc/test-id?delete_relationships=true")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_nodes_by_property_success(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test successful nodes by property endpoint."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.get_nodes_by_property.return_value = [{"id": "1", "properties": {"name": "test"}}]
        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/nodes/Module/tech_cc?property_name=name&property_value=test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    def test_search_nodes_success(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test successful node search endpoint."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.search_nodes.return_value = [{"id": "1", "properties": {"name": "test"}}]
        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/search?search_text=test")

        assert response.status_code == 200

    def test_search_nodes_no_filters(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test node search with no filters."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.search_nodes.return_value = []
        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/search")

        assert response.status_code == 200

    def test_create_relationship_success(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test successful relationship creation endpoint."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.create_relationship.return_value = {
            "id": "rel-id",
            "type": "CONTAINS",
            "start_node": "node-1",
            "end_node": "node-2",
        }
        # Override the dependency
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

        assert response.status_code == 200

    def test_get_node_relationships_success(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test successful node relationships endpoint."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.get_node_relationships.return_value = [{"type": "CONTAINS", "related_node": "node-2"}]
        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/nodes/Module/tech_cc/node-1/relationships")

        assert response.status_code == 200

    def test_get_node_relationships_all_directions(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test node relationships in all directions."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.get_node_relationships.return_value = []
        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/nodes/Module/tech_cc/node-1/relationships?direction=both")

        assert response.status_code == 200

    def test_invalid_node_type(self, client: Any) -> None:
        """Test with invalid node type."""
        node_data = {"node_type": "InvalidType", "module": "tech_cc", "properties": {"name": "test-node"}}
        response = client.post("/v1/graph/nodes", json=node_data)

        assert response.status_code == 422

    def test_invalid_module_label(self, client: Any) -> None:
        """Test with invalid module label."""
        node_data = {"node_type": "Module", "module": "invalid_module", "properties": {"name": "test-node"}}
        response = client.post("/v1/graph/nodes", json=node_data)

        assert response.status_code == 422

    def test_invalid_relationship_type(self, client: Any) -> None:
        """Test with invalid relationship type."""
        rel_data = {
            "relationship_type": "INVALID_REL",
            "start_node_type": "Module",
            "start_module": "tech_cc",
            "start_node_id": "node-1",
            "end_node_type": "Module",
            "end_module": "tech_cc",
            "end_node_id": "node-2",
        }
        response = client.post("/v1/graph/relationships", json=rel_data)

        assert response.status_code == 422

    def test_server_error_handling(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test server error handling."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.get_graph_stats.side_effect = Exception("Database error")
        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/stats")

        assert response.status_code == 500

    def test_endpoint_parameter_validation(self, client: Any) -> None:
        """Test endpoint parameter validation."""
        # Missing required JSON body
        response = client.post("/v1/graph/nodes")

        assert response.status_code == 422

    def test_missing_required_parameters(self, client: Any) -> None:
        """Test handling of missing required parameters."""
        # Missing node_type in request body
        node_data = {"module": "tech_cc", "properties": {"name": "test-node"}}
        response = client.post("/v1/graph/nodes", json=node_data)

        assert response.status_code == 422

    def test_response_schemas(self, client: Any, app: Any, setup_mock_dependencies: Any) -> None:
        """Test that response schemas are properly structured."""
        # Import GraphService dependency
        from src.graph.router import get_graph_service

        # Configure mock service
        mock_service = AsyncMock()
        mock_service.get_graph_stats.return_value = {
            "total_nodes": 42,
            "total_relationships": 24,
            "node_types": {"Module": 10},
        }
        # Override the dependency
        app.dependency_overrides[get_graph_service] = lambda: mock_service

        response = client.get("/v1/graph/stats")

        assert response.status_code == 200
        data = response.json()

        # Check response schema structure
        assert "success" in data
        assert "data" in data
        assert "message" in data
        assert isinstance(data["success"], bool)
        assert isinstance(data["data"], dict)
