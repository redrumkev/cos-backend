# COS Architecture v1.0
**Purpose:** Definitive technical blueprint for all COS modules.

## I. Hybrid Vertical Slice + Atomic Design
- Each module is a self-contained vertical slice with its own main entry, routers, models, services
- Within each slice, functions are broken into atomic, testable units
- Benefits: AI-readability, token efficiency, clear ownership, independent testability
- Foundation for seamless module replication and scaling

## II. Standard Module Structure
```file_structure
backend/
├── module_name/
│   ├── module_name_main.py  # FastAPI app, lifespan events, ex: cc_main.py, pem_main.py
│   ├── router.py            # API endpoints
│   ├── schemas.py           # Pydantic validation models
│   ├── services.py          # Business logic
│   ├── models.py            # SQLAlchemy models with dynamic schema
│   ├── deps.py              # FastAPI dependencies
│   ├── crud.py              # Database operations
│   ├── utils.py             # Module-specific utilities
│   ├── tests/               # All module tests
│   │   ├── test_main.py
│   │   ├── test_services.py
│   │   └── ...
│   └── module_name_map.yaml # AI-friendly module manifest
```

## III. Key File Purposes & Components

### module_name_main.py
- FastAPI application creation and configuration
- Router mounting
- Lifespan events (startup/shutdown)
- Middleware attachment

### router.py
- APIRouter definition with prefix/tags
- Endpoint functions with dependency injection
- Request validation via Pydantic schemas
- Response formatting and status codes

### schemas.py
- Request validation models
- Response models
- Internal data transfer objects
- Nested models and relationships

### services.py
- Core business logic
- Orchestration of CRUD operations
- Error handling and validation
- Module-specific workflows

### models.py
- SQLAlchemy models with Table Args for schema
- Dynamic schema binding via config.settings
- Relationship definitions
- Index and constraint specifications

### deps.py
- Database session dependency
- Authentication/authorization dependencies
- Feature flags or configuration injection
- Shared request processing functions

### crud.py
- Direct database operations
- Query building and execution
- Transaction management
- Bulk operations and optimizations

## IV. Cross-Module Communication
- REST API calls (HTTP client) for synchronous operations
- Redis pub/sub for asynchronous events and notifications
- No direct Python imports between modules
- Shared data access only through database (isolated schemas)

## V. Common Directory Usage
- Strict inclusion criteria: truly universal code only
- Standard utilities: config, database, redis_client, logging
- Base classes that multiple modules inherit from
- Never module-specific code or business logic

## VI. Module Map YAML Structure
```yaml
# module_name_map.yaml
module:
  name: "module_name"
  description: "Core purpose statement"
  version: "1.0"

  files:
    - path: "module_name_main.py"
      purpose: "FastAPI application definition"
      dependencies: ["router.py", "common/config.py"]

    - path: "router.py"
      purpose: "API endpoints"
      dependencies: ["services.py", "schemas.py", "deps.py"]

    # Additional files listed with purposes and dependencies

  database:
    schema: "module_name"
    tables: ["primary_records", "related_items"]

  api_endpoints:
    - path: "/items"
      methods: ["GET", "POST"]
      purpose: "Item management"

    # Additional endpoints listed with purposes

  integrations:
    - module: "cc"
      purpose: "Configuration and logging"

    # Other module integrations listed
VII. Module Generation & Evolution

Use generate_module.py script to clone gold standard
Takes source module (e.g., cc) and creates target (e.g., pem)
Updates all references, imports, and configurations
Generates passing test suite for new module
Preserves structure while allowing module-specific extensions

Copy
### 4. `cos_implementation_plan.md` - The Roadmap

This streamlined implementation plan provides a clear path forward with concrete, actionable steps.
