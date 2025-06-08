"""FastAPI router for graph operations.

This module provides REST API endpoints for graph operations,
following the router pattern established in the cc module.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.graph.base import Neo4jClient, get_async_neo4j
from src.graph.registry import ModuleLabel, NodeType, RelationshipType
from src.graph.service import GraphService


# Pydantic models for API request/response
class NodeCreate(BaseModel):
    """Request model for creating a node."""

    node_type: NodeType
    module: ModuleLabel
    properties: dict[str, Any]
    unique_property: str | None = None


class NodeUpdate(BaseModel):
    """Request model for updating a node."""

    properties: dict[str, Any]


class RelationshipCreate(BaseModel):
    """Request model for creating a relationship."""

    from_node_id: str | int
    from_node_type: NodeType
    from_module: ModuleLabel
    to_node_id: str | int
    to_node_type: NodeType
    to_module: ModuleLabel
    relationship_type: RelationshipType
    properties: dict[str, Any] | None = None


class NodeResponse(BaseModel):
    """Response model for node operations."""

    success: bool
    data: dict[str, Any] | None = None
    message: str


class NodesResponse(BaseModel):
    """Response model for multiple nodes."""

    success: bool
    data: list[dict[str, Any]]
    count: int
    message: str


class RelationshipResponse(BaseModel):
    """Response model for relationship operations."""

    success: bool
    data: dict[str, Any] | None = None
    message: str


class GraphStatsResponse(BaseModel):
    """Response model for graph statistics."""

    success: bool
    data: dict[str, Any]
    message: str


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    driver_type: str
    connected: bool
    message: str


# Create the router
router = APIRouter(
    prefix="/graph",
    tags=["graph"],
    responses={404: {"description": "Not found"}},
)


# Dependencies
async def get_graph_service(client: Neo4jClient = Depends(get_async_neo4j)) -> GraphService:
    """Get graph service instance."""
    return GraphService(client)


# Health endpoints
@router.get("/health", response_model=HealthResponse)
async def health_check(client: Neo4jClient = Depends(get_async_neo4j)) -> HealthResponse:
    """Check the health of the graph database connection."""
    try:
        is_connected = await client.verify_connectivity() if client.is_connected else False
        driver_type = "rust" if "rust" in str(type(client.driver)).lower() else "standard"

        return HealthResponse(
            status="healthy" if is_connected else "unhealthy",
            driver_type=driver_type,
            connected=is_connected,
            message="Graph database connection is working" if is_connected else "Graph database connection failed",
        )
    except Exception as e:
        return HealthResponse(
            status="error", driver_type="unknown", connected=False, message=f"Health check failed: {e!s}"
        )


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(service: GraphService = Depends(get_graph_service)) -> GraphStatsResponse:
    """Get statistics about the graph structure."""
    try:
        stats = await service.get_graph_stats()
        return GraphStatsResponse(success=True, data=stats, message="Graph statistics retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get graph stats: {e!s}") from None


# Node endpoints
@router.post("/nodes", response_model=NodeResponse)
async def create_node(node_data: NodeCreate, service: GraphService = Depends(get_graph_service)) -> NodeResponse:
    """Create a new node in the graph."""
    try:
        result = await service.create_node(
            node_data.node_type, node_data.module, node_data.properties, node_data.unique_property
        )
        return NodeResponse(success=True, data=result, message=f"Created {node_data.node_type.value} node successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create node: {e!s}") from None


@router.get("/nodes/{node_type}/{module}/{node_id}", response_model=NodeResponse)
async def get_node(
    node_type: NodeType,
    module: ModuleLabel,
    node_id: str | int,
    service: GraphService = Depends(get_graph_service),
) -> NodeResponse:
    """Get a specific node by its ID."""
    try:
        result = await service.get_node(node_type, module, node_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Node not found")

        return NodeResponse(success=True, data=result, message=f"Retrieved {node_type.value} node successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get node: {e!s}") from None


@router.put("/nodes/{node_type}/{module}/{node_id}", response_model=NodeResponse)
async def update_node(
    node_type: NodeType,
    module: ModuleLabel,
    node_id: str | int,
    node_data: NodeUpdate,
    service: GraphService = Depends(get_graph_service),
) -> NodeResponse:
    """Update an existing node."""
    try:
        result = await service.update_node(node_type, module, node_id, node_data.properties)
        if result is None:
            raise HTTPException(status_code=404, detail="Node not found")

        return NodeResponse(success=True, data=result, message=f"Updated {node_type.value} node successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update node: {e!s}") from None


@router.delete("/nodes/{node_type}/{module}/{node_id}", response_model=NodeResponse)
async def delete_node(
    node_type: NodeType,
    module: ModuleLabel,
    node_id: str | int,
    delete_relationships: bool = Query(True, description="Whether to delete relationships as well"),
    service: GraphService = Depends(get_graph_service),
) -> NodeResponse:
    """Delete a node from the graph."""
    try:
        success = await service.delete_node(node_type, module, node_id, delete_relationships)
        if not success:
            raise HTTPException(status_code=404, detail="Node not found")

        return NodeResponse(success=True, data=None, message=f"Deleted {node_type.value} node successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete node: {e!s}") from None


@router.get("/nodes/{node_type}/{module}", response_model=NodesResponse)
async def get_nodes_by_property(
    node_type: NodeType,
    module: ModuleLabel,
    property_name: str = Query(..., description="Property name to filter by"),
    property_value: str = Query(..., description="Property value to match"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    service: GraphService = Depends(get_graph_service),
) -> NodesResponse:
    """Get nodes by a specific property value."""
    try:
        results = await service.get_nodes_by_property(node_type, module, property_name, property_value, limit)
        return NodesResponse(
            success=True, data=results, count=len(results), message=f"Retrieved {len(results)} {node_type.value} nodes"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get nodes: {e!s}") from None


@router.get("/search", response_model=NodesResponse)
async def search_nodes(
    node_type: NodeType | None = Query(None, description="Filter by node type"),
    module: ModuleLabel | None = Query(None, description="Filter by module"),
    search_text: str | None = Query(None, description="Text to search in node properties"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    service: GraphService = Depends(get_graph_service),
) -> NodesResponse:
    """Search for nodes with flexible criteria."""
    try:
        results = await service.search_nodes(node_type=node_type, module=module, search_text=search_text, limit=limit)
        return NodesResponse(
            success=True, data=results, count=len(results), message=f"Found {len(results)} matching nodes"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search nodes: {e!s}") from None


# Relationship endpoints
@router.post("/relationships", response_model=RelationshipResponse)
async def create_relationship(
    rel_data: RelationshipCreate, service: GraphService = Depends(get_graph_service)
) -> RelationshipResponse:
    """Create a relationship between two nodes."""
    try:
        result = await service.create_relationship(
            rel_data.from_node_id,
            rel_data.from_node_type,
            rel_data.from_module,
            rel_data.to_node_id,
            rel_data.to_node_type,
            rel_data.to_module,
            rel_data.relationship_type,
            rel_data.properties,
        )
        return RelationshipResponse(
            success=True, data=result, message=f"Created {rel_data.relationship_type.value} relationship successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create relationship: {e!s}") from None


@router.get("/nodes/{node_type}/{module}/{node_id}/relationships", response_model=list[dict[str, Any]])
async def get_node_relationships(
    node_type: NodeType,
    module: ModuleLabel,
    node_id: str | int,
    direction: str = Query("both", regex="^(in|out|both)$", description="Direction of relationships"),
    relationship_type: RelationshipType | None = Query(None, description="Filter by relationship type"),
    service: GraphService = Depends(get_graph_service),
) -> list[dict[str, Any]]:
    """Get all relationships for a specific node."""
    try:
        results = await service.get_node_relationships(node_id, node_type, module, direction, relationship_type)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get relationships: {e!s}") from None


# Schema information endpoints
@router.get("/schema")
async def get_schema_info() -> dict[str, Any]:
    """Get schema information about available node types, modules, and relationships."""
    from src.graph.registry import GraphRegistry

    return GraphRegistry.get_schema_info()
