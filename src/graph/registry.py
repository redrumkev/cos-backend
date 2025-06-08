"""Neo4j graph registry for managing node labels and relationships.

This module provides utilities for managing the dual-label pattern:
- Primary label: Node type (e.g., :Module, :Prompt, :Entity)
- Secondary label: Module namespace (e.g., :tech_cc, :content_pem)

Follows the pattern established in COS architecture documentation.
"""

from enum import Enum
from typing import Any

from src.common.logger import log_event


class NodeType(str, Enum):
    """Primary node types in the COS graph layer."""

    MODULE = "Module"
    PROMPT = "Prompt"
    ENTITY = "Entity"
    CONCEPT = "Concept"
    RELATIONSHIP = "Relationship"
    SESSION = "Session"
    LOG_ENTRY = "LogEntry"


class ModuleLabel(str, Enum):
    """Module namespace labels for dual-label pattern."""

    TECH_CC = "tech_cc"
    # Future modules will be added here as they are created
    # CONTENT_PEM = "content_pem"
    # ANALYTICS_AE = "analytics_ae"


class RelationshipType(str, Enum):
    """Standard relationship types in the COS graph."""

    CONTAINS = "CONTAINS"
    REFERENCES = "REFERENCES"
    DEPENDS_ON = "DEPENDS_ON"
    CREATED_BY = "CREATED_BY"
    TRIGGERED_BY = "TRIGGERED_BY"
    FLOWS_TO = "FLOWS_TO"
    RELATES_TO = "RELATES_TO"


class GraphRegistry:
    """Registry for managing Neo4j graph structure and queries."""

    @staticmethod
    def get_labels(node_type: NodeType, module: ModuleLabel) -> list[str]:
        """Get Neo4j labels for a node based on type and module.

        Args:
        ----
            node_type: The primary type of the node
            module: The module namespace for the node

        Returns:
        -------
            List of label strings in the format [":Type", ":module_namespace"]

        """
        return [f":{node_type.value}", f":{module.value}"]

    @staticmethod
    def format_labels_for_cypher(node_type: NodeType, module: ModuleLabel) -> str:
        """Format labels for use in Cypher queries.

        Args:
        ----
            node_type: The primary type of the node
            module: The module namespace for the node

        Returns:
        -------
            Formatted string for Cypher queries (e.g., ":Module:tech_cc")

        """
        labels = GraphRegistry.get_labels(node_type, module)
        return "".join(labels)

    @staticmethod
    def create_node_query(
        node_type: NodeType, module: ModuleLabel, properties: dict[str, Any] | None = None, return_node: bool = True
    ) -> str:
        """Generate Cypher query to create a node with proper labels.

        Args:
        ----
            node_type: The primary type of the node
            module: The module namespace for the node
            properties: Optional properties dictionary for the node
            return_node: Whether to return the created node

        Returns:
        -------
            Cypher CREATE query string

        """
        labels = GraphRegistry.format_labels_for_cypher(node_type, module)
        props_clause = " $props" if properties is not None else ""
        return_clause = " RETURN n" if return_node else ""

        return f"CREATE (n{labels}{props_clause}){return_clause}"

    @staticmethod
    def match_node_query(
        node_type: NodeType, module: ModuleLabel, where_clause: str | None = None, return_clause: str = "n"
    ) -> str:
        """Generate Cypher query to match nodes with specific labels.

        Args:
        ----
            node_type: The primary type of the node
            module: The module namespace for the node
            where_clause: Optional WHERE clause conditions
            return_clause: What to return (default: "n")

        Returns:
        -------
            Cypher MATCH query string

        """
        labels = GraphRegistry.format_labels_for_cypher(node_type, module)
        where = f" WHERE {where_clause}" if where_clause else ""

        return f"MATCH (n{labels}){where} RETURN {return_clause}"

    @staticmethod
    def create_relationship_query(
        from_node_type: NodeType,
        from_module: ModuleLabel,
        to_node_type: NodeType,
        to_module: ModuleLabel,
        relationship_type: RelationshipType,
        from_where: str | None = None,
        to_where: str | None = None,
        rel_properties: dict[str, Any] | None = None,
    ) -> str:
        """Generate Cypher query to create a relationship between nodes.

        Args:
        ----
            from_node_type: Type of the source node
            from_module: Module of the source node
            to_node_type: Type of the target node
            to_module: Module of the target node
            relationship_type: Type of relationship to create
            from_where: WHERE clause for source node
            to_where: WHERE clause for target node
            rel_properties: Optional properties for the relationship

        Returns:
        -------
            Cypher query to create the relationship

        """
        from_labels = GraphRegistry.format_labels_for_cypher(from_node_type, from_module)
        to_labels = GraphRegistry.format_labels_for_cypher(to_node_type, to_module)

        from_clause = f"WHERE {from_where}" if from_where else ""
        to_clause = f"WHERE {to_where}" if to_where else ""

        rel_props = ""
        if rel_properties:
            rel_props = " $rel_props"

        return f"""
        MATCH (a{from_labels}) {from_clause}
        MATCH (b{to_labels}) {to_clause}
        CREATE (a)-[r:{relationship_type.value}{rel_props}]->(b)
        RETURN r
        """.strip()

    @staticmethod
    def get_all_node_types() -> set[str]:
        """Get all available node types."""
        return {node_type.value for node_type in NodeType}

    @staticmethod
    def get_all_modules() -> set[str]:
        """Get all available module labels."""
        return {module.value for module in ModuleLabel}

    @staticmethod
    def get_all_relationship_types() -> set[str]:
        """Get all available relationship types."""
        return {rel_type.value for rel_type in RelationshipType}

    @staticmethod
    def validate_node_structure(node_type: str, module: str, properties: dict[str, Any] | None = None) -> bool:
        """Validate that a node structure conforms to COS standards.

        Args:
        ----
            node_type: The node type to validate
            module: The module label to validate
            properties: Optional properties to validate

        Returns:
        -------
            True if valid, False otherwise

        """
        try:
            # Validate node type
            NodeType(node_type)

            # Validate module
            ModuleLabel(module)

            # Log validation success
            log_event(
                source="graph",
                data={
                    "node_type": node_type,
                    "module": module,
                    "has_properties": bool(properties),
                },
                tags=["validation", "success"],
                memo="Node structure validation passed",
            )

            return True

        except ValueError as e:
            log_event(
                source="graph",
                data={
                    "node_type": node_type,
                    "module": module,
                    "error": str(e),
                },
                tags=["validation", "error"],
                memo="Node structure validation failed",
            )
            return False

    @staticmethod
    def get_schema_info() -> dict[str, Any]:
        """Get comprehensive schema information for the graph.

        Returns
        -------
            Dictionary containing all node types, modules, and relationships

        """
        return {
            "node_types": list(GraphRegistry.get_all_node_types()),
            "modules": list(GraphRegistry.get_all_modules()),
            "relationship_types": list(GraphRegistry.get_all_relationship_types()),
            "dual_label_pattern": ":<NodeType>:<module_namespace>",
            "examples": {
                "module_node": GraphRegistry.format_labels_for_cypher(NodeType.MODULE, ModuleLabel.TECH_CC),
                "prompt_node": GraphRegistry.format_labels_for_cypher(NodeType.PROMPT, ModuleLabel.TECH_CC),
            },
        }
