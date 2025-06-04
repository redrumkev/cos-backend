"""Tests for graph service layer."""

from unittest.mock import AsyncMock, patch

import pytest

from src.graph.base import Neo4jClient
from src.graph.registry import ModuleLabel, NodeType, RelationshipType
from src.graph.service import GraphService


class TestGraphService:
    """Test cases for GraphService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock(spec=Neo4jClient)
        self.service = GraphService(self.mock_client)

    @pytest.mark.asyncio
    async def test_get_graph_stats_success(self):
        """Test successful stats retrieval."""
        # Mock query results - the service calls execute_query 4 times for different stats
        self.mock_client.execute_query.side_effect = [
            [{"count": 100}],  # Total nodes
            [{"count": 50}],  # Total relationships
            [
                {"labels": ["Module", "tech_cc"], "count": 10},
                {"labels": ["Prompt", "tech_cc"], "count": 90},
            ],  # Node types
            [{"type": "CONTAINS", "count": 25}],  # Relationship types
        ]

        stats = await self.service.get_graph_stats()

        assert stats["total_nodes"] == 100
        assert stats["total_relationships"] == 50
        # Note: node_types returns raw results, not processed dict
        assert len(stats["node_types"]) == 2
        assert stats["node_types"][0]["count"] == 10

    @pytest.mark.asyncio
    async def test_create_node_success(self):
        """Test successful node creation."""
        # Mock successful validation and creation
        with (
            patch("src.graph.service.GraphRegistry.validate_node_structure", return_value=True),
            patch("src.graph.service.GraphRegistry.create_node_query", return_value="CREATE (n) RETURN n"),
        ):
            self.mock_client.execute_query.return_value = [{"n": {"id": "test-id", "name": "test-node"}}]

            result = await self.service.create_node(NodeType.MODULE, ModuleLabel.TECH_CC, {"name": "test-node"})

            assert result["id"] == "test-id"
            assert result["name"] == "test-node"

    @pytest.mark.asyncio
    async def test_create_node_validation_error(self):
        """Test node creation with validation error."""
        # Mock validation failure
        with (
            patch("src.graph.service.GraphRegistry.validate_node_structure", return_value=False),
            pytest.raises(ValueError, match="Invalid node structure"),
        ):
            await self.service.create_node(NodeType.MODULE, ModuleLabel.TECH_CC, {})

    @pytest.mark.asyncio
    async def test_get_node_success(self):
        """Test successful node retrieval by ID."""
        # Mock node found
        with patch("src.graph.service.GraphRegistry.match_node_query", return_value="MATCH (n) RETURN n"):
            self.mock_client.execute_query.return_value = [{"n": {"id": "test-id", "name": "test-node"}}]

            result = await self.service.get_node(NodeType.MODULE, ModuleLabel.TECH_CC, "test-id")

            assert result["id"] == "test-id"
            assert result["name"] == "test-node"

    @pytest.mark.asyncio
    async def test_get_node_not_found(self):
        """Test node retrieval when node not found."""
        # Mock no results
        with patch("src.graph.service.GraphRegistry.match_node_query", return_value="MATCH (n) RETURN n"):
            self.mock_client.execute_query.return_value = []

            result = await self.service.get_node(NodeType.MODULE, ModuleLabel.TECH_CC, "missing-id")

            assert result is None

    @pytest.mark.asyncio
    async def test_update_node_success(self):
        """Test successful node update."""
        # Mock successful update
        self.mock_client.execute_query.return_value = [{"n": {"id": "test-id", "name": "updated-name"}}]

        result = await self.service.update_node(
            NodeType.MODULE, ModuleLabel.TECH_CC, "test-id", {"name": "updated-name"}
        )

        assert result["id"] == "test-id"
        assert result["name"] == "updated-name"

    @pytest.mark.asyncio
    async def test_delete_node_success(self):
        """Test successful node deletion."""
        # Mock successful deletion
        self.mock_client.execute_query.return_value = [{"deleted_count": 1}]

        result = await self.service.delete_node(NodeType.MODULE, ModuleLabel.TECH_CC, "test-id", True)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_node_not_found(self):
        """Test node deletion when node not found."""
        # Mock no deletion (node not found)
        self.mock_client.execute_query.return_value = [{"deleted_count": 0}]

        result = await self.service.delete_node(NodeType.MODULE, ModuleLabel.TECH_CC, "missing-id", True)

        assert result is False

    @pytest.mark.asyncio
    async def test_create_relationship_success(self):
        """Test successful relationship creation."""
        # Mock successful relationship creation
        self.mock_client.execute_query.return_value = [{"r": {"type": "CONTAINS", "created_at": "2023-01-01"}}]

        result = await self.service.create_relationship(
            "from-id",
            NodeType.MODULE,
            ModuleLabel.TECH_CC,
            "to-id",
            NodeType.PROMPT,
            ModuleLabel.TECH_CC,
            RelationshipType.CONTAINS,
            {"weight": 1.0},
        )

        assert result["type"] == "CONTAINS"

    @pytest.mark.asyncio
    async def test_get_node_relationships_success(self):
        """Test successful node relationships retrieval."""
        # Mock relationship results - service expects records with 'r' key
        self.mock_client.execute_query.return_value = [{"r": {"type": "CONTAINS", "id": "rel-1"}}]

        results = await self.service.get_node_relationships(
            "test-id", NodeType.MODULE, ModuleLabel.TECH_CC, "out", RelationshipType.CONTAINS
        )

        assert len(results) == 1
        assert results[0]["type"] == "CONTAINS"

    @pytest.mark.asyncio
    async def test_get_node_relationships_all_directions(self):
        """Test node relationships retrieval for all directions."""
        # Mock relationship results
        self.mock_client.execute_query.return_value = []

        await self.service.get_node_relationships("test-id", NodeType.MODULE, ModuleLabel.TECH_CC, "both", None)

        # Verify the query was called
        assert self.mock_client.execute_query.called

    @pytest.mark.asyncio
    async def test_search_nodes_success(self):
        """Test successful node search."""
        # Mock search results
        self.mock_client.execute_query.return_value = [{"n": {"id": "1", "name": "test-node"}}]

        results = await self.service.search_nodes(NodeType.MODULE, ModuleLabel.TECH_CC, "test", None, 10)

        assert len(results) == 1
        assert results[0]["id"] == "1"

    @pytest.mark.asyncio
    async def test_get_nodes_by_property_success(self):
        """Test successful node retrieval by property."""
        # Mock property search results
        with patch("src.graph.service.GraphRegistry.match_node_query", return_value="MATCH (n) RETURN n"):
            self.mock_client.execute_query.return_value = [
                {"n": {"id": "1", "status": "active"}},
                {"n": {"id": "2", "status": "active"}},
            ]

            results = await self.service.get_nodes_by_property(
                NodeType.MODULE, ModuleLabel.TECH_CC, "status", "active", 10
            )

            assert len(results) == 2
            assert results[0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_empty_results_handling(self):
        """Test handling of empty results from database."""
        # Mock empty results
        self.mock_client.execute_query.return_value = []

        # Test various methods with empty results
        stats = await self.service.get_graph_stats()
        # Should handle empty gracefully with defaults
        assert isinstance(stats, dict)

        search_results = await self.service.search_nodes()
        assert search_results == []

    @pytest.mark.asyncio
    async def test_query_parameter_passing(self):
        """Test that query parameters are properly passed to the client."""
        # Mock successful query
        with patch(
            "src.graph.service.GraphRegistry.match_node_query", return_value="MATCH (n) WHERE n.id = $node_id RETURN n"
        ):
            self.mock_client.execute_query.return_value = [{"n": {"id": "test"}}]

            await self.service.get_node(NodeType.MODULE, ModuleLabel.TECH_CC, "test-id")

            # Verify the client was called with correct parameters
            self.mock_client.execute_query.assert_called_with(
                "MATCH (n) WHERE n.id = $node_id RETURN n", {"node_id": "test-id"}
            )

    @pytest.mark.asyncio
    async def test_relationship_direction_handling(self):
        """Test proper handling of relationship directions."""
        self.mock_client.execute_query.return_value = []

        # Test each direction
        for direction in ["in", "out", "both"]:
            await self.service.get_node_relationships("test-id", NodeType.MODULE, ModuleLabel.TECH_CC, direction, None)

        # Should have made 3 calls
        assert self.mock_client.execute_query.call_count == 3
