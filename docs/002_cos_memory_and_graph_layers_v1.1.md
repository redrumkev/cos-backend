# COS Memory & Graph Layers v1.1 (Condensed)

## I. Layered Overview
- Multi-layer data: optimized for speed, persistence, semantic intelligence.
- Goal: Scalable, resilient, supports quantum autopoiesis.

## II. Data Layers

### 2.1. L1: Ephemeral `mem0` (Per-Module Scratchpad)
- `mem0_<module>` Postgres schema.
- Stores: agent prompt traces, logs, temp state.
- Fast writes, module silo, clears/archives as needed.
- Access: `common/logger.py` for writes, direct SQLAlchemy for reads.

### 2.2. L1.R: Shared Redis Cache & Pub/Sub
- `mem0_redis` (Redis Stack).
- System-wide cache and async event bus.
- Access via `src/common/redis_client.py`.

### 2.3. L2: Semantic Graph Layer (Neo4j)
- Nodes: `<Type>:<module_namespace>` (e.g., `:Prompt:tech_pem`).
- Stores/interlinks concepts, prompts, entities, relationships.
- Enables multi-hop, semantic retrieval (Zettelkasten style).
- Models: `src/graph/modules/<domain>/<module>/graph_models.py`.

### 2.4. L3: ZK Author Layer (Curated KB)
- Markdown+YAML (Zettelkasten).
- Stores: distilled insights, MBQs, book source, quote origins.
- Feeds authored/publishable content.

### 2.5. L4: Ground Truth DB (Canonical)
- Module-specific Postgres schemas (`<module>`) for permanent operational data.
- True system of record; SQLAlchemy via each module's `models.py`.

## III. Data Flow & Evolution
- Flow: L1 logs → L2 graph → L3 curation → L4 record.
- Redis connects all layers/events/cache.
- **Quantum Autopoiesis:** Layers feed, evolve, and refine each other, driving system learning and self-alignment.
