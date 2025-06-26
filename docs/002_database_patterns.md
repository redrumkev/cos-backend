# Database Patterns & Standards

## PostgreSQL Schema Isolation
```python
# Primary schema (L4 canonical data)
class PrimaryModel(Base):
    __tablename__ = "table_name"
    __table_args__ = {"schema": "cc"}  # Module-specific schema

# Mem0 schema (L1 ephemeral data)
class Mem0Model(Base):
    __tablename__ = "base_log"
    __table_args__ = {"schema": "mem0_cc"}  # Module mem0 schema
Required L1 Mem0 Tables
pythonclass BaseLog:
    id: UUID (PK)
    timestamp: DateTime
    source_module: str
    request_id: str
    trace_id: str

class PromptTrace:
    id: UUID (PK)
    base_log_id: UUID (FK → BaseLog.id)
    role: str
    content: Text
    tokens_in: int
    tokens_out: int

class EventLog:
    id: UUID (PK)
    base_log_id: UUID (FK → BaseLog.id)
    event_type: str
    payload: JSONB
Redis Pub/Sub Patterns
python# Channel naming: <topic>.<module>
CHANNEL_NAME = f"mem0.recorded.{MODULE_NAME}"

# Message format (JSON)
{
  "base_log_id": "uuid-string",
  "event_type": "prompt_trace|event_log",
  "timestamp": "ISO-8601",
  "trace_id": "logfire-trace-id",
  "data": {...}  # PromptTrace or EventLog content
}
Neo4j Graph Patterns
python# Dual-label convention: :<Type>:<Module>
":Prompt:cc", ":Entity:cc", ":Event:cc"

# Common relationships
"(:Prompt)-[:REPLIED_WITH]->(:Prompt)"
"(:Prompt)-[:TRIGGERED]->(:Event)"
"(:Prompt)-[:CONTAINS_ENTITY]->(:Entity)"
