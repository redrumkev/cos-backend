# mem0 Manifest

## Purpose
`mem0` is the COS scratchpad: an ephemeral memory layer for agents, prompt workflows, and context-aware actions. It stores medium-term cognitive states outside PostgreSQL.

## Core Responsibilities
- Store/retrieve JSON payloads by key (`/memory/{id}`)
- Enable agent context recall (e.g., PEM, AIC, Cursor)
- Serve as a programmable AI-accessible memory node

## Endpoints
- `GET /memory/{id}` → returns memory
- `POST /memory/{id}` → saves memory
- `GET /ping` → healthcheck

## Typical Uses
- PEM logs prompt runs + result snapshots
- Cursor context for current file/module
- Agent memory cache: last message, next task, recent failures

## Storage Location
- Host volume: `E:/mem0_data/`
- Inside container: `/app/memory/`

## Future Expansion
- Memory tagging (e.g., short-term, long-term)
- Time-to-live support or scheduled decay
- Retrieval scoring (recency, priority)
- Event broadcasting (pub/sub to Redis)

## Design Philosophy
- Modular and replaceable
- Externalized cognition, not logic
- Decoupled from persistence (PostgreSQL is truth)
- Agent-agnostic, universally accessible
