"""Router path mapping helpers for testing.

This module provides standardized router path mapping helpers to handle
endpoint path changes due to router structure reorganization.
"""


def get_test_endpoint_path(endpoint_name: str, module: str = "cc") -> str:
    """Map endpoint names to current router paths.

    Args:
    ----
        endpoint_name: The endpoint name (e.g., "health", "modules", "debug")
        module: The module name (e.g., "cc", "graph")

    Returns:
    -------
        str: The full path to the endpoint

    Example:
    -------
        >>> get_test_endpoint_path("health", "cc")
        "/cc/health"
        >>> get_test_endpoint_path("modules", "cc")
        "/cc/modules"

    """
    # Base endpoint mapping for each module
    cc_endpoints = {
        "health": "/cc/health",
        "status": "/cc/status",
        "config": "/cc/config",
        "modules": "/cc/modules",
        "debug": "/cc/debug",
        "mem0": "/cc/mem0",
    }

    graph_endpoints = {
        "health": "/graph/health",
        "nodes": "/graph/nodes",
        "relationships": "/graph/relationships",
    }

    # Select the appropriate endpoint map
    if module == "cc":
        endpoint_map = cc_endpoints
    elif module == "graph":
        endpoint_map = graph_endpoints
    else:
        raise ValueError(f"Unsupported module: {module}")

    # Return the mapped path or the original endpoint name if not found
    return endpoint_map.get(endpoint_name, f"/{module}/{endpoint_name}")


def get_versioned_endpoint_path(endpoint_name: str, module: str = "cc", version: str = "v1") -> str:
    """Get versioned endpoint path.

    Args:
    ----
        endpoint_name: The endpoint name (e.g., "health", "modules", "debug")
        module: The module name (e.g., "cc", "graph")
        version: The API version (e.g., "v1", "v2")

    Returns:
    -------
        str: The full versioned path to the endpoint

    Example:
    -------
        >>> get_versioned_endpoint_path("modules", "cc", "v1")
        "/v1/cc/modules"
        >>> get_versioned_endpoint_path("health", "cc")
        "/v1/cc/health"

    """
    base_path = get_test_endpoint_path(endpoint_name, module)
    return f"/{version}{base_path}"


def get_module_resource_path(resource_id: str, module: str = "cc", version: str = "v1") -> str:
    """Get path for a specific module resource.

    Args:
    ----
        resource_id: The resource ID (UUID or identifier)
        module: The module name (e.g., "cc", "graph")
        version: The API version (e.g., "v1", "v2")

    Returns:
    -------
        str: The full path to the resource

    Example:
    -------
        >>> get_module_resource_path("123e4567-e89b-12d3-a456-426614174000", "cc")
        "/v1/cc/modules/123e4567-e89b-12d3-a456-426614174000"

    """
    modules_path = get_versioned_endpoint_path("modules", module, version)
    return f"{modules_path}/{resource_id}"


def get_debug_endpoint_path(debug_type: str, module: str = "cc") -> str:
    """Get debug endpoint path for a specific debug type.

    Args:
    ----
        debug_type: The debug endpoint type (e.g., "log", "redis-health")
        module: The module name (e.g., "cc", "graph")

    Returns:
    -------
        str: The full path to the debug endpoint

    Example:
    -------
        >>> get_debug_endpoint_path("log", "cc")
        "/cc/debug/log"
        >>> get_debug_endpoint_path("redis-health", "cc")
        "/cc/debug/redis-health"

    """
    debug_base = get_test_endpoint_path("debug", module)
    return f"{debug_base}/{debug_type}"


# Convenience mappings for common test scenarios
TEST_ENDPOINT_MAPPINGS: dict[str, str] = {
    # CC module endpoints
    "cc_health": "/cc/health",
    "cc_status": "/cc/status",
    "cc_config": "/cc/config",
    "cc_modules": "/cc/modules",
    "cc_debug_log": "/cc/debug/log",
    "cc_debug_redis": "/cc/debug/redis-health",
    "cc_mem0_notes": "/cc/mem0/notes",
    "cc_mem0_stats": "/cc/mem0/stats",
    # Versioned CC module endpoints
    "v1_cc_health": "/v1/cc/health",
    "v1_cc_status": "/v1/cc/status",
    "v1_cc_config": "/v1/cc/config",
    "v1_cc_modules": "/v1/cc/modules",
    "v1_cc_debug_log": "/v1/cc/debug/log",
    "v1_cc_debug_redis": "/v1/cc/debug/redis-health",
    "v1_cc_mem0_notes": "/v1/cc/mem0/notes",
    "v1_cc_mem0_stats": "/v1/cc/mem0/stats",
    # Graph module endpoints
    "graph_health": "/graph/health",
    "graph_nodes": "/graph/nodes",
    "graph_relationships": "/graph/relationships",
    # Versioned graph module endpoints
    "v1_graph_health": "/v1/graph/health",
    "v1_graph_nodes": "/v1/graph/nodes",
    "v1_graph_relationships": "/v1/graph/relationships",
}
