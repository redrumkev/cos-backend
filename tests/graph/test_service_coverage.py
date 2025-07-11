"""Additional tests for service.py to achieve 99.5%+ coverage.

Tests cover edge cases and rarely-hit code paths not covered in main test file.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.graph.base import Neo4jClient
from src.graph.registry import ModuleLabel, NodeType, RelationshipType
from src.graph.service import GraphService


class TestGraphServiceCoverage:
    """Additional test cases for graph service coverage."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_client = AsyncMock(spec=Neo4jClient)
        self.service = GraphService(self.mock_client)

    @pytest.mark.asyncio
    async def test_create_node_with_unique_property(self) -> None:
        """Test node creation with unique property (merge path) - lines 48-49."""
        # Mock successful validation and merge
        with (
            patch("src.graph.service.GraphRegistry.validate_node_structure", return_value=True),
        ):
            self.mock_client.execute_query.return_value = [{"n": {"id": "unique-id", "email": "test@example.com"}}]

            result = await self.service.create_node(
                NodeType.MODULE,
                ModuleLabel.TECH_CC,
                {"email": "test@example.com", "name": "Test User"},
                unique_property="email",
            )

            assert result["id"] == "unique-id"
            assert result["email"] == "test@example.com"

            # Verify merge query was used (check the query contains MERGE)
            called_query = self.mock_client.execute_query.call_args[0][0]
            assert "MERGE" in called_query

    @pytest.mark.asyncio
    async def test_create_node_failure(self) -> None:
        """Test node creation when query returns empty result - line 69."""
        # Mock successful validation but empty result
        with (
            patch("src.graph.service.GraphRegistry.validate_node_structure", return_value=True),
            patch("src.graph.service.GraphRegistry.create_node_query", return_value="CREATE (n) RETURN n"),
        ):
            self.mock_client.execute_query.return_value = []  # Empty result

            with pytest.raises(RuntimeError, match="Failed to create node"):
                await self.service.create_node(NodeType.MODULE, ModuleLabel.TECH_CC, {"name": "test-node"})

    @pytest.mark.asyncio
    async def test_update_node_not_found(self) -> None:
        """Test update node when node not found - line 168."""
        # Mock empty result (node not found)
        self.mock_client.execute_query.return_value = []

        result = await self.service.update_node(
            NodeType.MODULE, ModuleLabel.TECH_CC, "nonexistent-id", {"name": "updated-name"}
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_node_without_relationships(self) -> None:
        """Test node deletion without deleting relationships - line 196."""
        # Mock successful deletion without relationships
        self.mock_client.execute_query.return_value = [{"deleted_count": 1}]

        result = await self.service.delete_node(
            NodeType.MODULE, ModuleLabel.TECH_CC, "test-id", delete_relationships=False
        )

        assert result is True

        # Verify the query doesn't use DETACH DELETE
        called_query = self.mock_client.execute_query.call_args[0][0]
        assert "DETACH DELETE" not in called_query
        assert "DELETE n" in called_query

    @pytest.mark.asyncio
    async def test_create_relationship_failure(self) -> None:
        """Test relationship creation when query returns empty result - line 281."""
        # Mock empty result
        self.mock_client.execute_query.return_value = []

        with pytest.raises(RuntimeError, match="Failed to create relationship"):
            await self.service.create_relationship(
                "from-id",
                NodeType.MODULE,
                ModuleLabel.TECH_CC,
                "to-id",
                NodeType.PROMPT,
                ModuleLabel.TECH_CC,
                RelationshipType.CONTAINS,
            )

    @pytest.mark.asyncio
    async def test_search_nodes_with_node_type_only(self) -> None:
        """Test search nodes with only node_type filter - line 357."""
        self.mock_client.execute_query.return_value = [{"n": {"id": "1", "type": "Module"}}]

        results = await self.service.search_nodes(
            node_type=NodeType.MODULE,
            module=None,  # No module filter
            search_text=None,
            limit=10,
        )

        assert len(results) == 1

        # Verify the query uses only node type
        called_query = self.mock_client.execute_query.call_args[0][0]
        assert "MATCH (n:Module)" in called_query

    @pytest.mark.asyncio
    async def test_search_nodes_with_module_only(self) -> None:
        """Test search nodes with only module filter - line 359."""
        self.mock_client.execute_query.return_value = [{"n": {"id": "1", "module": "tech_cc"}}]

        results = await self.service.search_nodes(
            node_type=None,  # No node type filter
            module=ModuleLabel.TECH_CC,
            search_text=None,
            limit=10,
        )

        assert len(results) == 1

        # Verify the query uses only module
        called_query = self.mock_client.execute_query.call_args[0][0]
        assert "MATCH (n:tech_cc)" in called_query

    @pytest.mark.asyncio
    async def test_search_nodes_with_properties_filter(self) -> None:
        """Test search nodes with properties filter - lines 375-378."""
        self.mock_client.execute_query.return_value = [{"n": {"id": "1", "status": "active", "priority": "high"}}]

        results = await self.service.search_nodes(
            node_type=None,
            module=None,
            search_text=None,
            properties={"status": "active", "priority": "high"},  # Properties filter
            limit=10,
        )

        assert len(results) == 1

        # Verify parameters were passed correctly
        called_params = self.mock_client.execute_query.call_args[0][1]
        assert "prop_status" in called_params
        assert "prop_priority" in called_params
        assert called_params["prop_status"] == "active"
        assert called_params["prop_priority"] == "high"

    @pytest.mark.asyncio
    async def test_build_merge_query(self) -> None:
        """Test _build_merge_query method - lines 389-390."""
        query = self.service._build_merge_query(NodeType.MODULE, ModuleLabel.TECH_CC, "email")

        # Verify the query structure
        assert "MERGE" in query
        assert "{email: $props.email}" in query
        assert "ON CREATE SET n = $props" in query
        assert "ON MATCH SET n += $props" in query
        assert "RETURN n" in query

    @pytest.mark.asyncio
    async def test_create_relationship_without_properties(self) -> None:
        """Test relationship creation without properties."""
        self.mock_client.execute_query.return_value = [{"r": {"type": "CONTAINS"}}]

        result = await self.service.create_relationship(
            "from-id",
            NodeType.MODULE,
            ModuleLabel.TECH_CC,
            "to-id",
            NodeType.PROMPT,
            ModuleLabel.TECH_CC,
            RelationshipType.CONTAINS,
            properties=None,  # No properties
        )

        assert result["type"] == "CONTAINS"

        # Verify params don't include rel_props
        called_params = self.mock_client.execute_query.call_args[0][1]
        assert "rel_props" not in called_params

    @pytest.mark.asyncio
    async def test_get_graph_stats_with_empty_results(self) -> None:
        """Test graph stats handling when some queries return empty."""
        # Mock mixed results - some empty, some with data
        self.mock_client.execute_query.side_effect = [
            [],  # Empty total nodes
            [{"count": 50}],  # Total relationships
            [],  # Empty node types
            [{"type": "CONTAINS", "count": 25}],  # Relationship types
        ]

        stats = await self.service.get_graph_stats()

        # Should handle empty results gracefully
        assert stats["total_nodes"] == 0  # Default for empty result
        assert stats["total_relationships"] == 50
        assert stats["node_types"] == []  # Empty list
        assert len(stats["relationship_types"]) == 1

    @pytest.mark.asyncio
    async def test_search_nodes_with_all_filters(self) -> None:
        """Test search nodes with all possible filters combined."""
        self.mock_client.execute_query.return_value = [{"n": {"id": "1", "name": "Test Module", "status": "active"}}]

        results = await self.service.search_nodes(
            node_type=NodeType.MODULE,
            module=ModuleLabel.TECH_CC,
            search_text="Test",
            properties={"status": "active"},
            limit=5,
        )

        assert len(results) == 1

        # Verify all filters were applied
        called_query = self.mock_client.execute_query.call_args[0][0]
        called_params = self.mock_client.execute_query.call_args[0][1]

        assert ":Module:tech_cc" in called_query  # Both labels
        assert "search_text" in called_params
        assert "prop_status" in called_params
