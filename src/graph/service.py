"""Graph service layer for Neo4j operations.

This module provides high-level operations for managing graph nodes and relationships,
following the service pattern established in the cc module.
"""

from typing import Any

from src.common.logger import log_event
from src.graph.base import Neo4jClient
from src.graph.registry import GraphRegistry, ModuleLabel, NodeType, RelationshipType


class GraphService:
    """Service layer for graph operations."""

    def __init__(self, client: Neo4jClient) -> None:
        """Initialize the service with a Neo4j client."""
        self.client = client

    async def create_node(
        self,
        node_type: NodeType,
        module: ModuleLabel,
        properties: dict[str, Any],
        unique_property: str | None = None,
    ) -> dict[str, Any]:
        """Create a new node in the graph.

        Args:
        ----
            node_type: The type of node to create
            module: The module namespace for the node
            properties: Properties to set on the node
            unique_property: Optional property name to use for uniqueness constraint

        Returns:
        -------
            Dictionary representation of the created node

        """
        # Validate the node structure
        if not GraphRegistry.validate_node_structure(node_type.value, module.value, properties):
            raise ValueError(f"Invalid node structure for {node_type.value}:{module.value}")

        # Create or merge based on uniqueness constraint
        if unique_property and unique_property in properties:
            query = self._build_merge_query(node_type, module, unique_property)
            result = await self.client.execute_query(query, {"props": properties})
        else:
            query = GraphRegistry.create_node_query(node_type, module, properties)
            result = await self.client.execute_query(query, {"props": properties})

        if result:
            node_data = result[0]["n"]
            log_event(
                source="graph",
                data={
                    "operation": "create_node",
                    "node_type": node_type.value,
                    "module": module.value,
                    "node_id": node_data.get("id"),
                },
                tags=["service", "create", "success"],
                memo=f"Created {node_type.value} node in {module.value}",
            )
            return node_data

        raise RuntimeError("Failed to create node")

    async def get_node(self, node_type: NodeType, module: ModuleLabel, node_id: str | int) -> dict[str, Any] | None:
        """Retrieve a node by its ID.

        Args:
        ----
            node_type: The type of node to retrieve
            module: The module namespace for the node
            node_id: The ID of the node to retrieve

        Returns:
        -------
            Dictionary representation of the node, or None if not found

        """
        where_clause = "n.id = $node_id"
        query = GraphRegistry.match_node_query(node_type, module, where_clause)

        result = await self.client.execute_query(query, {"node_id": node_id})

        if result:
            return result[0]["n"]
        return None

    async def get_nodes_by_property(
        self, node_type: NodeType, module: ModuleLabel, property_name: str, property_value: Any, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve nodes by a specific property value.

        Args:
        ----
            node_type: The type of nodes to retrieve
            module: The module namespace for the nodes
            property_name: The property name to filter by
            property_value: The property value to match
            limit: Maximum number of nodes to return

        Returns:
        -------
            List of dictionary representations of the nodes

        """
        where_clause = f"n.{property_name} = $property_value"
        query = GraphRegistry.match_node_query(node_type, module, where_clause)
        query += f" LIMIT {limit}"

        result = await self.client.execute_query(query, {"property_value": property_value})

        return [record["n"] for record in result]

    async def update_node(
        self, node_type: NodeType, module: ModuleLabel, node_id: str | int, properties: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update properties of an existing node.

        Args:
        ----
            node_type: The type of node to update
            module: The module namespace for the node
            node_id: The ID of the node to update
            properties: Properties to update on the node

        Returns:
        -------
            Dictionary representation of the updated node, or None if not found

        """
        labels = GraphRegistry.format_labels_for_cypher(node_type, module)

        # Build the SET clause dynamically
        set_clauses = [f"n.{key} = $props.{key}" for key in properties]
        set_clause = ", ".join(set_clauses)

        query = f"""
        MATCH (n{labels}) WHERE n.id = $node_id
        SET {set_clause}
        RETURN n
        """

        result = await self.client.execute_query(query, {"node_id": node_id, "props": properties})

        if result:
            log_event(
                source="graph",
                data={
                    "operation": "update_node",
                    "node_type": node_type.value,
                    "module": module.value,
                    "node_id": node_id,
                    "updated_properties": list(properties.keys()),
                },
                tags=["service", "update", "success"],
                memo=f"Updated {node_type.value} node {node_id}",
            )
            return result[0]["n"]

        return None

    async def delete_node(
        self, node_type: NodeType, module: ModuleLabel, node_id: str | int, delete_relationships: bool = True
    ) -> bool:
        """Delete a node from the graph.

        Args:
        ----
            node_type: The type of node to delete
            module: The module namespace for the node
            node_id: The ID of the node to delete
            delete_relationships: Whether to delete relationships as well

        Returns:
        -------
            True if the node was deleted, False if not found

        """
        labels = GraphRegistry.format_labels_for_cypher(node_type, module)

        if delete_relationships:
            query = f"""
            MATCH (n{labels}) WHERE n.id = $node_id
            DETACH DELETE n
            RETURN count(n) as deleted_count
            """
        else:
            query = f"""
            MATCH (n{labels}) WHERE n.id = $node_id
            DELETE n
            RETURN count(n) as deleted_count
            """

        result = await self.client.execute_query(query, {"node_id": node_id})

        if result and result[0]["deleted_count"] > 0:
            log_event(
                source="graph",
                data={
                    "operation": "delete_node",
                    "node_type": node_type.value,
                    "module": module.value,
                    "node_id": node_id,
                    "detach_delete": delete_relationships,
                },
                tags=["service", "delete", "success"],
                memo=f"Deleted {node_type.value} node {node_id}",
            )
            return True

        return False

    async def create_relationship(
        self,
        from_node_id: str | int,
        from_node_type: NodeType,
        from_module: ModuleLabel,
        to_node_id: str | int,
        to_node_type: NodeType,
        to_module: ModuleLabel,
        relationship_type: RelationshipType,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a relationship between two nodes.

        Args:
        ----
            from_node_id: ID of the source node
            from_node_type: Type of the source node
            from_module: Module of the source node
            to_node_id: ID of the target node
            to_node_type: Type of the target node
            to_module: Module of the target node
            relationship_type: Type of relationship to create
            properties: Optional properties for the relationship

        Returns:
        -------
            Dictionary representation of the created relationship

        """
        from_where = "a.id = $from_id"
        to_where = "b.id = $to_id"

        query = GraphRegistry.create_relationship_query(
            from_node_type, from_module, to_node_type, to_module, relationship_type, from_where, to_where, properties
        )

        params = {
            "from_id": from_node_id,
            "to_id": to_node_id,
        }
        if properties:
            params["rel_props"] = properties

        result = await self.client.execute_query(query, params)

        if result:
            relationship_data = result[0]["r"]
            log_event(
                source="graph",
                data={
                    "operation": "create_relationship",
                    "from_node": f"{from_node_type.value}:{from_node_id}",
                    "to_node": f"{to_node_type.value}:{to_node_id}",
                    "relationship_type": relationship_type.value,
                },
                tags=["service", "relationship", "success"],
                memo=f"Created {relationship_type.value} relationship",
            )
            return relationship_data

        raise RuntimeError("Failed to create relationship")

    async def get_node_relationships(
        self,
        node_id: str | int,
        node_type: NodeType,
        module: ModuleLabel,
        direction: str = "both",  # "in", "out", or "both"
        relationship_type: RelationshipType | None = None,
    ) -> list[dict[str, Any]]:
        """Get all relationships for a node.

        Args:
        ----
            node_id: ID of the node
            node_type: Type of the node
            module: Module of the node
            direction: Direction of relationships ("in", "out", or "both")
            relationship_type: Optional specific relationship type to filter by

        Returns:
        -------
            List of relationship dictionaries

        """
        labels = GraphRegistry.format_labels_for_cypher(node_type, module)

        # Build relationship pattern based on direction
        if direction == "in":
            rel_pattern = "<-[r]-()"
        elif direction == "out":
            rel_pattern = "-[r]->()"
        else:  # both
            rel_pattern = "-[r]-()"

        # Add relationship type filter if specified
        if relationship_type:
            rel_pattern = rel_pattern.replace("[r]", f"[r:{relationship_type.value}]")

        query = f"""
        MATCH (n{labels}){rel_pattern}
        WHERE n.id = $node_id
        RETURN r
        """

        result = await self.client.execute_query(query, {"node_id": node_id})
        return [record["r"] for record in result]

    async def search_nodes(
        self,
        node_type: NodeType | None = None,
        module: ModuleLabel | None = None,
        search_text: str | None = None,
        properties: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search for nodes with flexible criteria.

        Args:
        ----
            node_type: Optional node type filter
            module: Optional module filter
            search_text: Optional text to search in node properties
            properties: Optional specific property filters
            limit: Maximum number of results to return

        Returns:
        -------
            List of matching nodes

        """
        # Build the MATCH clause
        if node_type and module:
            labels = GraphRegistry.format_labels_for_cypher(node_type, module)
            match_clause = f"MATCH (n{labels})"
        elif node_type:
            match_clause = f"MATCH (n:{node_type.value})"
        elif module:
            match_clause = f"MATCH (n:{module.value})"
        else:
            match_clause = "MATCH (n)"

        # Build WHERE conditions
        where_conditions = []
        params = {}

        if search_text:
            # Search in common text properties
            where_conditions.append(
                "(n.name CONTAINS $search_text OR n.title CONTAINS $search_text OR n.description CONTAINS $search_text)"
            )
            params["search_text"] = search_text

        if properties:
            for key, value in properties.items():
                condition_key = f"prop_{key}"
                where_conditions.append(f"n.{key} = ${condition_key}")
                params[condition_key] = value

        # Combine query parts
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        query = f"{match_clause}{where_clause} RETURN n LIMIT {limit}"

        result = await self.client.execute_query(query, params)
        return [record["n"] for record in result]

    def _build_merge_query(self, node_type: NodeType, module: ModuleLabel, unique_property: str) -> str:
        """Build a MERGE query for creating unique nodes."""
        labels = GraphRegistry.format_labels_for_cypher(node_type, module)
        return f"""
        MERGE (n{labels} {{{unique_property}: $props.{unique_property}}})
        ON CREATE SET n = $props
        ON MATCH SET n += $props
        RETURN n
        """

    async def get_graph_stats(self) -> dict[str, Any]:
        """Get statistics about the graph structure.

        Returns
        -------
            Dictionary containing graph statistics

        """
        stats_queries = {
            "total_nodes": "MATCH (n) RETURN count(n) as count",
            "total_relationships": "MATCH ()-[r]->() RETURN count(r) as count",
            "node_types": "MATCH (n) RETURN labels(n) as labels, count(n) as count",
            "relationship_types": "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count",
        }

        stats = {}
        for stat_name, query in stats_queries.items():
            result = await self.client.execute_query(query)
            if stat_name in ["total_nodes", "total_relationships"]:
                stats[stat_name] = result[0]["count"] if result else 0
            else:
                stats[stat_name] = result

        return stats
