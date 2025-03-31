"""Mem0 memory client interface.

This module provides a client for interacting with the Mem0 memory service.
The client exposes simple get/set operations for storing and retrieving
structured memory blocks.
"""

from typing import Any

import httpx


class Mem0Client:
    """Client for interacting with Mem0 memory service."""

    def __init__(self, base_url: str = "http://localhost:7790") -> None:
        """Initialize the client with the base URL.

        Args:
        ----
            base_url: The base URL of the Mem0 service (default: "http://localhost:7790")

        """
        self.base_url = base_url

    def get(self, key: str) -> dict[str, Any]:
        """Retrieve a memory block by key.

        Args:
        ----
            key: The memory block key

        Returns:
        -------
            The memory block data

        """
        r = httpx.get(f"{self.base_url}/memory/{key}")
        r.raise_for_status()
        result: dict[str, Any] = r.json()
        return result

    def set(self, key: str, value: dict[str, Any]) -> dict[str, Any]:
        """Store a memory block by key.

        Args:
        ----
            key: The memory block key
            value: The memory block data to store

        Returns:
        -------
            The storage operation result

        """
        r = httpx.post(f"{self.base_url}/memory/{key}", json=value)
        r.raise_for_status()
        result: dict[str, Any] = r.json()
        return result


def get_client() -> Mem0Client:
    """Get a Mem0Client instance with default settings.

    Returns
    -------
        A configured Mem0Client instance

    """
    return Mem0Client()


if __name__ == "__main__":
    # Simple test functionality when run directly
    from common.logger import logger

    client = get_client()
    data_to_set: dict[str, Any] = {"msg": "Hello from client"}
    key_to_test = "test-client-main"

    logger.info(f"Setting data for key '{key_to_test}': {data_to_set}")
    client.set(key_to_test, data_to_set)

    retrieved_data: dict[str, Any] = client.get(key_to_test)
    logger.info(f"Retrieved data for key '{key_to_test}': {retrieved_data}")
