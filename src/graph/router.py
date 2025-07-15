"""FastAPI router for graph operations.

This module provides REST API endpoints for graph operations,
following the router pattern established in the cc module.

Pattern Reference: router.py v3.0.0 (Research-Driven Implementation)
Applied: create_module_router factory pattern
Applied: RFC 9457 Problem Details for error responses
Applied: Annotated[Type, Depends()] dependency injection
Applied: ModuleDeps for bundled dependencies
Applied: Request ID propagation for tracing
"""

import copy
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends, Query, Request
from fastapi.routing import APIRoute
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.config import Settings, get_settings
from src.common.database import get_async_db
from src.common.request_id_middleware import get_request_id
from src.core_v2.patterns.error_handling import (
    COSError,
    ErrorCategory,
    NotFoundError,
    ValidationError,
)
from src.core_v2.patterns.router import (
    ModuleDeps,
    PaginationParams,
    RateLimitConfig,
    create_module_router,
)
from src.graph.base import Neo4jClient, get_async_neo4j
from src.graph.registry import GraphRegistry, ModuleLabel, NodeType, RelationshipType
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


# Create the router with new pattern (versioned for main app)
router = create_module_router(
    prefix="/graph",
    module=ModuleLabel.TECH_CC,  # Graph operations are part of CC module
    tags=["graph", "neo4j", "relationships"],
    version="v1",
    rate_limit=RateLimitConfig(requests_per_minute=200, burst_size=30),
)

# Create non-versioned router for testing purposes
router_test = create_module_router(
    prefix="/graph",
    module=ModuleLabel.TECH_CC,  # Graph operations are part of CC module
    tags=["graph", "neo4j", "relationships"],
    version=None,  # No version for testing
    rate_limit=RateLimitConfig(requests_per_minute=200, burst_size=30),
)


# Dependencies
async def get_graph_service(client: Neo4jClient = Depends(get_async_neo4j)) -> GraphService:
    """Get graph service instance."""
    return GraphService(client)


# Create module dependencies factory for this module
async def get_module_deps(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    background_tasks: BackgroundTasks,
) -> ModuleDeps:
    """Get module dependencies instance."""
    return ModuleDeps(
        module=ModuleLabel.TECH_CC,
        request=request,
        db=db,
        settings=settings,
        background_tasks=background_tasks,
        request_id=get_request_id(),
    )


# Health endpoints
@router.get("/health", response_model=HealthResponse)
async def health_check(
    client: Annotated[Neo4jClient, Depends(get_async_neo4j)],
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> HealthResponse:
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
async def get_graph_stats(
    service: Annotated[GraphService, Depends(get_graph_service)],
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> GraphStatsResponse:
    """Get statistics about the graph structure."""
    try:
        stats = await service.get_graph_stats()
        return GraphStatsResponse(success=True, data=stats, message="Graph statistics retrieved successfully")
    except Exception as e:
        raise COSError(
            message=f"Failed to get graph stats: {e!s}",
            category=ErrorCategory.EXTERNAL_SERVICE,
            details={"service": "neo4j"},
            user_message="Unable to retrieve graph statistics",
        ) from e


# Node endpoints
@router.post("/nodes", response_model=NodeResponse)
async def create_node(
    node_data: NodeCreate,
    service: Annotated[GraphService, Depends(get_graph_service)],
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> NodeResponse:
    """Create a new node in the graph."""
    try:
        result = await service.create_node(
            node_data.node_type, node_data.module, node_data.properties, node_data.unique_property
        )
        return NodeResponse(success=True, data=result, message=f"Created {node_data.node_type.value} node successfully")
    except ValueError as e:
        raise ValidationError(message=str(e), field="node_data", user_message=f"Invalid node data: {e}") from e
    except Exception as e:
        raise COSError(
            message=f"Failed to create node: {e!s}",
            category=ErrorCategory.EXTERNAL_SERVICE,
            details={"node_type": node_data.node_type.value},
            user_message="Unable to create node in graph database",
        ) from e


@router.get("/nodes/{node_type}/{module}/{node_id}", response_model=NodeResponse)
async def get_node(
    node_type: NodeType,
    module: ModuleLabel,
    node_id: str | int,
    service: Annotated[GraphService, Depends(get_graph_service)],
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> NodeResponse:
    """Get a specific node by its ID."""
    try:
        result = await service.get_node(node_type, module, node_id)
        if result is None:
            raise NotFoundError(
                resource=f"{node_type.value} node",
                identifier=node_id,
                user_message=f"Node {node_id} not found in graph",
            )

        return NodeResponse(success=True, data=result, message=f"Retrieved {node_type.value} node successfully")
    except (NotFoundError, COSError):
        raise
    except Exception as e:
        raise COSError(
            message=f"Failed to get node: {e!s}",
            category=ErrorCategory.EXTERNAL_SERVICE,
            details={"node_type": node_type.value, "node_id": str(node_id)},
            user_message="Unable to retrieve node from graph database",
        ) from e


@router.put("/nodes/{node_type}/{module}/{node_id}", response_model=NodeResponse)
async def update_node(
    node_type: NodeType,
    module: ModuleLabel,
    node_id: str | int,
    node_data: NodeUpdate,
    service: Annotated[GraphService, Depends(get_graph_service)],
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> NodeResponse:
    """Update an existing node."""
    try:
        result = await service.update_node(node_type, module, node_id, node_data.properties)
        if result is None:
            raise NotFoundError(
                resource=f"{node_type.value} node",
                identifier=node_id,
                user_message=f"Node {node_id} not found in graph",
            )

        return NodeResponse(success=True, data=result, message=f"Updated {node_type.value} node successfully")
    except (NotFoundError, COSError):
        raise
    except Exception as e:
        raise COSError(
            message=f"Failed to update node: {e!s}",
            category=ErrorCategory.EXTERNAL_SERVICE,
            details={"node_type": node_type.value, "node_id": str(node_id)},
            user_message="Unable to update node in graph database",
        ) from e


@router.delete("/nodes/{node_type}/{module}/{node_id}", response_model=NodeResponse)
async def delete_node(
    node_type: NodeType,
    module: ModuleLabel,
    node_id: str | int,
    service: Annotated[GraphService, Depends(get_graph_service)],
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
    delete_relationships: Annotated[bool, Query(description="Whether to delete relationships as well")] = True,
) -> NodeResponse:
    """Delete a node from the graph."""
    try:
        success = await service.delete_node(node_type, module, node_id, delete_relationships)
        if not success:
            raise NotFoundError(
                resource=f"{node_type.value} node",
                identifier=node_id,
                user_message=f"Node {node_id} not found in graph",
            )

        return NodeResponse(success=True, data=None, message=f"Deleted {node_type.value} node successfully")
    except (NotFoundError, COSError):
        raise
    except Exception as e:
        raise COSError(
            message=f"Failed to delete node: {e!s}",
            category=ErrorCategory.EXTERNAL_SERVICE,
            details={
                "node_type": node_type.value,
                "node_id": str(node_id),
                "delete_relationships": delete_relationships,
            },
            user_message="Unable to delete node from graph database",
        ) from e


@router.get("/nodes/{node_type}/{module}", response_model=NodesResponse)
async def get_nodes_by_property(
    node_type: NodeType,
    module: ModuleLabel,
    property_name: Annotated[str, Query(description="Property name to filter by")],
    property_value: Annotated[str, Query(description="Property value to match")],
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[GraphService, Depends(get_graph_service)],
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> NodesResponse:
    """Get nodes by a specific property value."""
    try:
        results = await service.get_nodes_by_property(
            node_type, module, property_name, property_value, pagination.limit
        )
        return NodesResponse(
            success=True, data=results, count=len(results), message=f"Retrieved {len(results)} {node_type.value} nodes"
        )
    except Exception as e:
        raise COSError(
            message=f"Failed to get nodes: {e!s}",
            category=ErrorCategory.EXTERNAL_SERVICE,
            details={"node_type": node_type.value, "property_name": property_name, "property_value": property_value},
            user_message="Unable to search nodes by property",
        ) from e


@router.get("/search", response_model=NodesResponse)
async def search_nodes(
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[GraphService, Depends(get_graph_service)],
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
    node_type: Annotated[NodeType | None, Query(description="Filter by node type")] = None,
    module: Annotated[ModuleLabel | None, Query(description="Filter by module")] = None,
    search_text: Annotated[str | None, Query(description="Text to search in node properties")] = None,
) -> NodesResponse:
    """Search for nodes with flexible criteria."""
    try:
        results = await service.search_nodes(
            node_type=node_type, module=module, search_text=search_text, limit=pagination.limit
        )
        return NodesResponse(
            success=True, data=results, count=len(results), message=f"Found {len(results)} matching nodes"
        )
    except Exception as e:
        raise COSError(
            message=f"Failed to search nodes: {e!s}",
            category=ErrorCategory.EXTERNAL_SERVICE,
            details={"search_text": search_text, "filters": {"node_type": node_type, "module": module}},
            user_message="Unable to search nodes in graph database",
        ) from e


# Relationship endpoints
@router.post("/relationships", response_model=RelationshipResponse)
async def create_relationship(
    rel_data: RelationshipCreate,
    service: Annotated[GraphService, Depends(get_graph_service)],
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
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
        raise COSError(
            message=f"Failed to create relationship: {e!s}",
            category=ErrorCategory.EXTERNAL_SERVICE,
            details={
                "relationship_type": rel_data.relationship_type.value,
                "from_node": str(rel_data.from_node_id),
                "to_node": str(rel_data.to_node_id),
            },
            user_message="Unable to create relationship in graph database",
        ) from e


@router.get("/nodes/{node_type}/{module}/{node_id}/relationships", response_model=list[dict[str, Any]])
async def get_node_relationships(
    node_type: NodeType,
    module: ModuleLabel,
    node_id: str | int,
    service: Annotated[GraphService, Depends(get_graph_service)],
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
    direction: Annotated[str, Query(pattern="^(in|out|both)$", description="Direction of relationships")] = "both",
    relationship_type: Annotated[RelationshipType | None, Query(description="Filter by relationship type")] = None,
) -> list[dict[str, Any]]:
    """Get all relationships for a specific node."""
    try:
        results = await service.get_node_relationships(node_id, node_type, module, direction, relationship_type)
        return results
    except Exception as e:
        raise COSError(
            message=f"Failed to get relationships: {e!s}",
            category=ErrorCategory.EXTERNAL_SERVICE,
            details={"node_id": str(node_id), "node_type": node_type.value, "direction": direction},
            user_message="Unable to retrieve node relationships from graph database",
        ) from e


# Schema information endpoints
@router.get("/schema")
async def get_schema_info(
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> dict[str, Any]:
    """Get schema information about available node types, modules, and relationships."""
    return GraphRegistry.get_schema_info()


# Copy all routes from the main router to the test router
# This ensures both routers have identical route definitions
# We need to create new routes with modified paths (remove /v1 prefix)
for route in router.routes:
    if (
        hasattr(route, "path")
        and hasattr(route, "methods")
        and isinstance(route, APIRoute)
        and route.path.startswith("/v1/graph/")
    ):
        # Create a new route with the non-versioned path
        new_route = copy.copy(route)
        new_route.path = route.path.replace("/v1/graph/", "/graph/")
        new_route.path_regex = None  # type: ignore  # Let FastAPI regenerate the path regex
        router_test.routes.append(new_route)
