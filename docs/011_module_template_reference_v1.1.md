# COS Module Template Reference v1.1 (Mama Bear Version)

module:
  name: "<module_name>"
  version: "1.0"
  description: "Describe core module purpose (1-2 lines)."
  alignment_mantra: "Optional: one-line soul/purpose statement."

  files:
    - path: "<module>_main.py"
      role: "FastAPI app, router mounting, lifespan."
    - path: "router.py"
      role: "Defines APIRouter endpoints for all API traffic."
      dependencies: ["schemas.py", "services.py", "deps.py"]
    - path: "schemas.py"
      role: "Pydantic models for request/response/internal validation."
    - path: "services.py"
      role: "Core business logic; orchestrates CRUD, logging."
    - path: "crud.py"
      role: "Direct SQLAlchemy DB operations for both primary and mem0 schemas."
    - path: "models.py"
      role: "ORM models for main Postgres schema."
    - path: "mem0_models.py"
      role: "ORM models for ephemeral mem0 Postgres schema."
    - path: "graph_models.py" # Optional
      role: "Neo4j node/relationship definitions (if module uses graph)."
    - path: "deps.py"
      role: "FastAPI dependencies: DB, Redis clients."
    - path: "utils.py" # Optional
      role: "Module utilities (non-core logic)."
    - path: "tests/"
      role: "All Pytest tests (unit, integration, API, model validation)."
      breakdown:
        - test_main.py: "Tests FastAPI app/lifespan logic."
        - test_router.py: "Tests API endpoints."
        - test_services.py: "Tests business logic/services."
        - test_crud.py: "Tests CRUD DB ops."
        - test_models.py: "Tests ORM model definitions."
        - test_mem0_models.py: "Tests mem0 ORM model definitions (optional)."
        - test_graph_models.py: "Tests Neo4j model logic (optional)."

  database:
    primary_schema:
      name: "<module>"
      purpose: "Canonical, persistent data."
      key_tables: ["list main tables"]
      models_file: "models.py"
    mem0_schema:
      name: "mem0_<module>"
      purpose: "Ephemeral agent log/scratchpad."
      key_tables: ["list ephemeral tables"]
      models_file: "mem0_models.py"

  graph_layer: # Optional
    domain: "<domain>"
    module_label_suffix: "<module>"
    purpose: "Semantic graph for interlinked knowledge."
    key_node_types: ["list main node types"]
    models_file: "graph_models.py"

  api_endpoints:
    - path: "/health"
      methods: ["GET"]
      purpose: "Basic health check."
      response_schema: "HealthStatus"
    - path: "/config"
      methods: ["GET"]
      purpose: "Module config."
      response_schema: "ModuleConfig"
    # Add further endpoints as needed

  integrations:
    - type: "common_service"
      name: "common/logger.py"
      purpose: "Structured logging to mem0."
    - type: "external_service_api"
      name: "<other_module>"
      method: "REST API"
      purpose: "Call another module."
      endpoints_used: ["/path"]
    - type: "message_bus_publish"
      channel: "<pubsub_channel>"
      purpose: "Publish events."
    - type: "message_bus_subscribe"
      channel: "<pubsub_channel>"
      purpose: "React to events."

  future_expansions:
    - name: "PlannedFeature"
      description: "Future module upgrade."
      priority: "High"
