# Control Center (CC) Module

## Purpose

The Control Center (CC) serves as the central hub of the Creative Operating System (COS). It coordinates all other modules, provides system-wide health monitoring, and serves as the orchestration layer for the entire system. All agent modules (PEM, AIC, VN, etc.) are initiated or monitored from here.

## Core Capabilities

- **Health Monitoring**: System-wide and module-specific health checks
- **Configuration Management**: Centralized configuration access and control
- **Module Coordination**: Inter-module communication and event orchestration
- **System Status Reporting**: Comprehensive reports on system operation

## Architecture

The CC module follows COS's Hybrid Vertical Slice + Atomic Composition pattern:

- **Self-contained**: No cross-module imports, only API or Redis communication
- **Vertically Complete**: Includes all layers from API to database
- **Atomic Components**: Each function has a single responsibility
- **100% Test Coverage**: Every component has comprehensive tests

## File Structure

- `cc_main.py`: FastAPI app initialization and router mounting
- `router.py`: API endpoint definitions
- `schemas.py`: Pydantic models for request/response validation
- `services.py`: Core business logic
- `models.py`: SQLAlchemy database models
- `deps.py`: FastAPI dependencies
- `crud.py`: Database operations
- `cc_manifest.yaml`: Module identity and purpose
- `cc_map.yaml`: Module structure map for AI readability

## API Endpoints

The CC module exposes the following endpoints:

- `GET /cc/health`: Basic health check for the CC module
- `GET /cc/config`: Get CC module configuration
- `GET /cc/system/health`: Comprehensive system health report
- `POST /cc/ping`: Ping specific module to check health

## Database Schema

The CC module operates in its own PostgreSQL schema named `cc` with the following tables:

- `health_status`: Track the health of all system modules
- `modules`: Configuration and activation status of modules

## Integration Points

The CC module integrates with:

- `mem0`: For memory storage and retrieval (via HTTP API)
- Other modules: Health checking and coordination (via HTTP API / Redis pub/sub)

## Development Guidelines

Follow these guidelines when working on the CC module:

1. **TDD First**: Write tests before implementation
2. **Type Safety**: Use strict mypy compliance and Pydantic models
3. **Zero Warnings**: Ensure zero linting or type checking warnings
4. **Docstrings**: Comprehensive documentation for all components
5. **Module Independence**: No cross-module imports

## Soul Alignment

*"Central intelligence that orchestrates the heartbeat of the system."*

The CC module is designed with these principles in mind:
- Clarity over complexity
- Stability over features
- Service over utility
- Interconnectedness over isolation

## Future Expansions

- **System-wide Event Bus**: Redis-based pub/sub system for event propagation
- **Command Queue**: Task queue for asynchronous operations
- **Admin Dashboard Integration**: API endpoints for administrative dashboards
