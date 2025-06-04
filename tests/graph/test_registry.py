"""Tests for graph registry module.

Tests cover node type management, label generation, and query construction
for the COS graph layer dual-label pattern.
"""

from __future__ import annotations

from src.graph.registry import (
    GraphRegistry,
    ModuleLabel,
    NodeType,
    RelationshipType,
)


class TestNodeType:
    """Test cases for NodeType enum."""

    def test_node_type_values(self) -> None:
        """Test that NodeType enum has expected values."""
        expected_types = {
            "MODULE",
            "PROMPT",
            "ENTITY",
            "CONCEPT",
            "RELATIONSHIP",
            "SESSION",
            "LOG_ENTRY",
        }
        actual_types = {nt.name for nt in NodeType}
        assert actual_types == expected_types

    def test_node_type_string_values(self) -> None:
        """Test that NodeType enum string values are correctly formatted."""
        assert NodeType.MODULE.value == "Module"
        assert NodeType.PROMPT.value == "Prompt"
        assert NodeType.ENTITY.value == "Entity"


class TestModuleLabel:
    """Test cases for ModuleLabel enum."""

    def test_module_label_values(self) -> None:
        """Test that ModuleLabel enum has expected values."""
        expected_labels = {"TECH_CC"}
        actual_labels = {ml.name for ml in ModuleLabel}
        assert actual_labels == expected_labels

    def test_module_label_string_values(self) -> None:
        """Test that ModuleLabel enum string values are correctly formatted."""
        assert ModuleLabel.TECH_CC.value == "tech_cc"


class TestRelationshipType:
    """Test cases for RelationshipType enum."""

    def test_relationship_type_values(self) -> None:
        """Test that RelationshipType enum has expected values."""
        expected_types = {
            "CONTAINS",
            "REFERENCES",
            "DEPENDS_ON",
            "CREATED_BY",
            "TRIGGERED_BY",
            "FLOWS_TO",
            "RELATES_TO",
        }
        actual_types = {rt.name for rt in RelationshipType}
        assert actual_types == expected_types


class TestGraphRegistry:
    """Test cases for GraphRegistry class."""

    def test_get_labels(self) -> None:
        """Test label generation for dual-label pattern."""
        labels = GraphRegistry.get_labels(NodeType.MODULE, ModuleLabel.TECH_CC)
        assert labels == [":Module", ":tech_cc"]

        labels = GraphRegistry.get_labels(NodeType.PROMPT, ModuleLabel.TECH_CC)
        assert labels == [":Prompt", ":tech_cc"]

    def test_format_labels_for_cypher(self) -> None:
        """Test label formatting for Cypher queries."""
        formatted = GraphRegistry.format_labels_for_cypher(NodeType.MODULE, ModuleLabel.TECH_CC)
        assert formatted == ":Module:tech_cc"

        formatted = GraphRegistry.format_labels_for_cypher(NodeType.PROMPT, ModuleLabel.TECH_CC)
        assert formatted == ":Prompt:tech_cc"

    def test_create_node_query_basic(self) -> None:
        """Test basic node creation query generation."""
        query = GraphRegistry.create_node_query(NodeType.MODULE, ModuleLabel.TECH_CC)
        expected = "CREATE (n:Module:tech_cc) RETURN n"
        assert query == expected

    def test_create_node_query_with_properties(self) -> None:
        """Test node creation query with properties."""
        query = GraphRegistry.create_node_query(
            NodeType.MODULE, ModuleLabel.TECH_CC, properties={"name": "test"}, return_node=True
        )
        expected = "CREATE (n:Module:tech_cc $props) RETURN n"
        assert query == expected

    def test_create_node_query_no_return(self) -> None:
        """Test node creation query without return clause."""
        query = GraphRegistry.create_node_query(NodeType.MODULE, ModuleLabel.TECH_CC, return_node=False)
        expected = "CREATE (n:Module:tech_cc)"
        assert query == expected

    def test_match_node_query_basic(self) -> None:
        """Test basic node matching query generation."""
        query = GraphRegistry.match_node_query(NodeType.MODULE, ModuleLabel.TECH_CC)
        expected = "MATCH (n:Module:tech_cc) RETURN n"
        assert query == expected

    def test_match_node_query_with_where(self) -> None:
        """Test node matching query with WHERE clause."""
        query = GraphRegistry.match_node_query(
            NodeType.MODULE, ModuleLabel.TECH_CC, where_clause="n.name = 'test'", return_clause="n.name"
        )
        expected = "MATCH (n:Module:tech_cc) WHERE n.name = 'test' RETURN n.name"
        assert query == expected

    def test_create_relationship_query_basic(self) -> None:
        """Test basic relationship creation query."""
        query = GraphRegistry.create_relationship_query(
            NodeType.MODULE,
            ModuleLabel.TECH_CC,
            NodeType.PROMPT,
            ModuleLabel.TECH_CC,
            RelationshipType.CONTAINS,
        )

        expected_parts = [
            "MATCH (a:Module:tech_cc)",
            "MATCH (b:Prompt:tech_cc)",
            "CREATE (a)-[r:CONTAINS]->(b)",
            "RETURN r",
        ]

        for part in expected_parts:
            assert part in query

    def test_create_relationship_query_with_conditions(self) -> None:
        """Test relationship creation query with WHERE conditions."""
        query = GraphRegistry.create_relationship_query(
            NodeType.MODULE,
            ModuleLabel.TECH_CC,
            NodeType.PROMPT,
            ModuleLabel.TECH_CC,
            RelationshipType.CONTAINS,
            from_where="a.name = 'module1'",
            to_where="b.id = 'prompt1'",
            rel_properties={"weight": 1.0},
        )

        expected_parts = [
            "MATCH (a:Module:tech_cc) WHERE a.name = 'module1'",
            "MATCH (b:Prompt:tech_cc) WHERE b.id = 'prompt1'",
            "CREATE (a)-[r:CONTAINS $rel_props]->(b)",
            "RETURN r",
        ]

        for part in expected_parts:
            assert part in query

    def test_get_all_node_types(self) -> None:
        """Test getting all available node types."""
        node_types = GraphRegistry.get_all_node_types()
        expected = {nt.value for nt in NodeType}
        assert node_types == expected

    def test_get_all_modules(self) -> None:
        """Test getting all available module labels."""
        modules = GraphRegistry.get_all_modules()
        expected = {ml.value for ml in ModuleLabel}
        assert modules == expected

    def test_get_all_relationship_types(self) -> None:
        """Test getting all available relationship types."""
        rel_types = GraphRegistry.get_all_relationship_types()
        expected = {rt.value for rt in RelationshipType}
        assert rel_types == expected

    def test_validate_node_structure_valid(self) -> None:
        """Test node structure validation with valid inputs."""
        result = GraphRegistry.validate_node_structure("Module", "tech_cc")
        assert result is True

        result = GraphRegistry.validate_node_structure("Prompt", "tech_cc", properties={"test": "value"})
        assert result is True

    def test_validate_node_structure_invalid_node_type(self) -> None:
        """Test node structure validation with invalid node type."""
        result = GraphRegistry.validate_node_structure("InvalidType", "tech_cc")
        assert result is False

    def test_validate_node_structure_invalid_module(self) -> None:
        """Test node structure validation with invalid module."""
        result = GraphRegistry.validate_node_structure("Module", "invalid_module")
        assert result is False

    def test_get_schema_info(self) -> None:
        """Test schema information retrieval."""
        schema = GraphRegistry.get_schema_info()

        assert "node_types" in schema
        assert "modules" in schema
        assert "relationship_types" in schema

        assert schema["node_types"] == list(GraphRegistry.get_all_node_types())
        assert schema["modules"] == list(GraphRegistry.get_all_modules())
        assert schema["relationship_types"] == list(GraphRegistry.get_all_relationship_types())
