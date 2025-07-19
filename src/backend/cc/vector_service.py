"""Vector operations service with Qdrant integration.

This service provides vector storage and similarity search functionality
for the CC module. Currently operates with graceful fallbacks when Qdrant
is not available.

TODO: Make Qdrant required and remove fallback logic (Sprint 3)
"""

import logging
from typing import Any
from uuid import uuid4

from qdrant_client.http.models import Distance, VectorParams

from src.common.logger import log_event
from src.common.qdrant_config import get_qdrant_config

logger = logging.getLogger(__name__)


class VectorService:
    """Service for vector operations with Qdrant."""

    def __init__(self) -> None:
        """Initialize vector service."""
        self.config = get_qdrant_config()
        self.collection_name = "cc_vectors"  # CC module vector collection

    async def initialize_collection(self) -> bool:
        """Initialize vector collection if Qdrant is available.

        Returns
        -------
            True if successful, False if Qdrant unavailable

        """
        client = await self.config.get_client()
        if not client:
            log_event(
                source="cc_vector_service",
                data={"action": "initialize_collection", "status": "skipped"},
                tags=["vector", "init", "fallback", "warning"],
                memo="Qdrant unavailable - skipping collection initialization",
            )
            return False

        try:
            # Check if collection exists
            collections = await client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                # Create collection with default config
                # TODO: Configure vector size and distance metric based on embedding model
                await client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # OpenAI ada-002 dimension
                        distance=Distance.COSINE,
                    ),
                )

                log_event(
                    source="cc_vector_service",
                    data={"action": "create_collection", "collection": self.collection_name},
                    tags=["vector", "init", "created"],
                    memo=f"Created vector collection: {self.collection_name}",
                )

            return True

        except Exception as e:
            log_event(
                source="cc_vector_service",
                data={"action": "initialize_collection", "error": str(e)},
                tags=["vector", "init", "error"],
                memo="Failed to initialize vector collection",
            )
            return False

    async def store_vector(
        self,
        vector: list[float],
        payload: dict[str, Any],
        vector_id: str | None = None,
    ) -> str | None:
        """Store a vector with associated metadata.

        Args:
        ----
            vector: Vector embeddings
            payload: Metadata to store with vector
            vector_id: Optional ID, generates UUID if not provided

        Returns:
        -------
            Vector ID if successful, None if Qdrant unavailable

        """
        client = await self.config.get_client()
        if not client:
            log_event(
                source="cc_vector_service",
                data={"action": "store_vector", "status": "skipped"},
                tags=["vector", "store", "fallback", "warning"],
                memo="Qdrant unavailable - vector storage skipped",
            )
            return None

        try:
            if vector_id is None:
                vector_id = str(uuid4())

            await client.upsert(
                collection_name=self.collection_name, points=[{"id": vector_id, "vector": vector, "payload": payload}]
            )

            log_event(
                source="cc_vector_service",
                data={"action": "store_vector", "vector_id": vector_id},
                tags=["vector", "store", "success"],
                memo=f"Stored vector: {vector_id}",
            )

            return vector_id

        except Exception as e:
            log_event(
                source="cc_vector_service",
                data={"action": "store_vector", "error": str(e)},
                tags=["vector", "store", "error"],
                memo="Failed to store vector",
            )
            return None

    async def search_similar(
        self,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors.

        Args:
        ----
            query_vector: Query vector for similarity search
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
        -------
            List of similar vectors with scores, empty list if unavailable

        """
        client = await self.config.get_client()
        if not client:
            log_event(
                source="cc_vector_service",
                data={"action": "search_similar", "status": "skipped"},
                tags=["vector", "search", "fallback", "warning"],
                memo="Qdrant unavailable - returning empty results",
            )
            return []

        try:
            results = await client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )

            # Format results
            formatted_results = [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                }
                for hit in results
            ]

            log_event(
                source="cc_vector_service",
                data={
                    "action": "search_similar",
                    "results_count": len(formatted_results),
                    "limit": limit,
                },
                tags=["vector", "search", "success"],
                memo=f"Found {len(formatted_results)} similar vectors",
            )

            return formatted_results

        except Exception as e:
            log_event(
                source="cc_vector_service",
                data={"action": "search_similar", "error": str(e)},
                tags=["vector", "search", "error"],
                memo="Failed to search vectors",
            )
            return []

    async def delete_vector(self, vector_id: str) -> bool:
        """Delete a vector by ID.

        Args:
        ----
            vector_id: ID of vector to delete

        Returns:
        -------
            True if successful, False otherwise

        """
        client = await self.config.get_client()
        if not client:
            log_event(
                source="cc_vector_service",
                data={"action": "delete_vector", "status": "skipped"},
                tags=["vector", "delete", "fallback", "warning"],
                memo="Qdrant unavailable - deletion skipped",
            )
            return False

        try:
            await client.delete(
                collection_name=self.collection_name,
                points_selector=[vector_id],
            )

            log_event(
                source="cc_vector_service",
                data={"action": "delete_vector", "vector_id": vector_id},
                tags=["vector", "delete", "success"],
                memo=f"Deleted vector: {vector_id}",
            )

            return True

        except Exception as e:
            log_event(
                source="cc_vector_service",
                data={"action": "delete_vector", "error": str(e)},
                tags=["vector", "delete", "error"],
                memo="Failed to delete vector",
            )
            return False

    async def health_check(self) -> dict[str, Any]:
        """Check vector service health.

        Returns
        -------
            Health status dictionary

        """
        qdrant_health = await self.config.health_check()

        return {
            "service": "vector_service",
            "qdrant": qdrant_health,
            "collection": self.collection_name,
            "status": "operational" if qdrant_health.get("status") == "healthy" else "degraded",
        }


# Global instance
_vector_service: VectorService | None = None


def get_vector_service() -> VectorService:
    """Get global vector service instance.

    Returns
    -------
        VectorService instance

    """
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service
