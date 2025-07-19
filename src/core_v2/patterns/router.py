"""Pattern: FastAPI Router Organization.

Version: 2025-07-15 v3.0.0 (Research-Driven Implementation)
ADR: ADR-002 (Living Patterns System)
Status: Gold Standard - Ready for Implementation

Purpose: Standardize FastAPI router organization across all COS modules
When to use: All API endpoint definitions and route organization
When NOT to use: Background tasks, WebSocket handlers, or non-HTTP interfaces

Research Sources:
- FastAPI 0.116+ official documentation (2025)
- GitHub Engineering API Design Guidelines
- Stripe API Architecture Patterns
- Context7 FastAPI best practices analysis
- O3 Expert Analysis (2025-07-15)

Anti-patterns to avoid:
- Mixing business logic in route handlers
- Inconsistent error responses across endpoints
- Direct database access in routes
- Hardcoded configuration values
- Missing request ID tracking
- Skipping input validation
- Ignoring performance metrics
"""

from collections.abc import Callable, Sequence
from typing import Annotated, Any, TypeVar

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.config import Settings, get_settings
from src.common.database import get_async_db
from src.common.request_id_middleware import get_request_id
from src.core_v2.patterns.error_handling import ERROR_TO_STATUS, COSError
from src.graph.registry import ModuleLabel

# Type aliases for cleaner signatures
type DbSession = Annotated[AsyncSession, Depends(get_async_db)]
type RequestId = str  # Request ID is injected via ModuleDeps
type AppSettings = Annotated[Settings, Depends(get_settings)]

T = TypeVar("T")


# RATE LIMITING CONFIGURATION
class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""

    requests_per_minute: int = Field(default=60, ge=1)
    burst_size: int = Field(default=10, ge=1)
    key_func: Callable[[Request], str] | None = None  # Extract rate limit key


# STANDARD ERROR RESPONSE MODEL (RFC 9457)
class ProblemDetail(BaseModel):
    """Standard error response following RFC 9457."""

    type: str = Field(description="Error type URI")
    title: str = Field(description="Short error description")
    status: int = Field(description="HTTP status code")
    detail: str | None = Field(default=None, description="Detailed error message")
    instance: str | None = Field(default=None, description="Specific occurrence URI")
    request_id: str | None = Field(default=None, description="Request correlation ID")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "/errors/validation",
                    "title": "Validation Error",
                    "status": 400,
                    "detail": "The 'email' field must be a valid email address",
                    "instance": "/users/123",
                    "request_id": "req_abc123",
                }
            ]
        }
    }


# CANONICAL ROUTER FACTORY
def create_module_router(
    *,
    prefix: str,
    module: ModuleLabel,
    tags: Sequence[str],
    version: str | None = None,
    dependencies: list[Any] | None = None,
    middlewares: Sequence[Callable[..., Any]] | None = None,
    rate_limit: RateLimitConfig | None = None,
) -> APIRouter:
    """Create a standardized router with COS conventions.

    Args:
    ----
        prefix: URL prefix for all routes (e.g., "/users")
        module: COS module identifier for isolation
        tags: OpenAPI tags for documentation
        version: API version (e.g., "v1", "v2")
        dependencies: List of FastAPI dependencies
        middlewares: Router-specific middleware functions
        rate_limit: Rate limiting configuration

    Returns:
    -------
        Configured APIRouter instance

    Example:
    -------
        router = create_module_router(
            prefix="/users",
            module=ModuleLabel.TECH_CC,
            tags=["users", "authentication"],
            version="v1",
            dependencies=[Depends(verify_token)],
            rate_limit=RateLimitConfig(requests_per_minute=100)
        )

    """
    # Apply version to prefix if provided
    versioned_tags = list(tags)
    if version:
        prefix = f"/{version}{prefix}"
        versioned_tags = [f"{tag} {version}" for tag in tags]

    # Build dependency list
    all_dependencies = dependencies or []

    # Add rate limiting dependency if configured
    if rate_limit:
        from src.common.rate_limiter import create_rate_limit_dependency

        all_dependencies.append(Depends(create_rate_limit_dependency(rate_limit)))

    # Create router with standard configuration
    router = APIRouter(
        prefix=prefix,
        tags=list(versioned_tags),
        dependencies=all_dependencies,
        responses={
            status.HTTP_400_BAD_REQUEST: {"model": ProblemDetail, "description": "Bad request"},
            status.HTTP_401_UNAUTHORIZED: {"model": ProblemDetail, "description": "Authentication required"},
            status.HTTP_403_FORBIDDEN: {"model": ProblemDetail, "description": "Insufficient permissions"},
            status.HTTP_404_NOT_FOUND: {"model": ProblemDetail, "description": "Resource not found"},
            status.HTTP_409_CONFLICT: {"model": ProblemDetail, "description": "Resource conflict"},
            status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ProblemDetail, "description": "Validation error"},
            status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ProblemDetail, "description": "Internal server error"},
            status.HTTP_502_BAD_GATEWAY: {"model": ProblemDetail, "description": "External service error"},
        },
    )

    # Apply router-specific middleware
    if middlewares:
        for middleware in middlewares:
            router.add_event_handler("startup", middleware)

    return router


# EXCEPTION HANDLERS
async def cos_error_handler(request: Request, exc: COSError) -> JSONResponse:
    """Handle COS-specific errors with standard format."""
    request_id = request.state.request_id if hasattr(request.state, "request_id") else None

    return JSONResponse(
        status_code=ERROR_TO_STATUS.get(exc.category, 500),
        content=ProblemDetail(
            type=f"/errors/{exc.category.value}",
            title=exc.category.value.replace("_", " ").title(),
            status=ERROR_TO_STATUS.get(exc.category, 500),
            detail=exc.user_message,
            instance=str(request.url),
            request_id=request_id,
        ).model_dump(exclude_none=True),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors with request body included in dev mode."""
    request_id = request.state.request_id if hasattr(request.state, "request_id") else None
    settings = get_settings()

    # Include body in development mode for debugging
    body = None
    if settings.ENVIRONMENT == "development":
        try:
            body = await request.body()
        except Exception as e:
            # Log the exception but continue processing
            import logging

            logging.getLogger(__name__).warning("Failed to read request body: %s", e)

    content = ProblemDetail(
        type="/errors/validation",
        title="Validation Error",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Request validation failed",
        instance=str(request.url),
        request_id=request_id,
    ).model_dump(exclude_none=True)

    # Add validation details
    content["errors"] = exc.errors()
    if body:
        content["body"] = body.decode("utf-8", errors="ignore")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=content,
    )


# STANDARD ROUTE PATTERNS
class PaginationParams(BaseModel):
    """Standard pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.limit


class BaseRouter:
    """Base class for module routers with standard patterns.

    Example:
    -------
        class UserRouter(BaseRouter):
            prefix = "/users"
            tags = ["users"]
            module = ModuleLabel.TECH_CC

            def __init__(self, service: UserService):
                self.service = service
                super().__init__()

            def _register_routes(self) -> None:
                @self.router.get("/", response_model=list[UserResponse])
                async def list_users(
                    pagination: Annotated[PaginationParams, Depends()],
                    db: DbSession,
                    request_id: RequestId,
                ) -> list[UserResponse]:
                    return await self.service.list_users(
                        db, pagination.limit, pagination.offset
                    )

    """

    # Override in subclass (abstract properties)
    prefix: str  # Must be set in subclass
    tags: Sequence[str]  # Must be set in subclass
    module: ModuleLabel  # Must be set in subclass
    version: str | None = None
    rate_limit: RateLimitConfig | None = None

    def __init__(self) -> None:
        """Initialize router with standard configuration."""
        self.router = create_module_router(
            prefix=self.prefix,
            module=self.module,
            tags=self.tags,
            version=self.version,
            rate_limit=self.rate_limit,
        )
        self._register_routes()
        self._register_error_handlers()

    def _register_routes(self) -> None:
        """Register all routes. Override in subclass."""
        raise NotImplementedError("Subclass must implement _register_routes")

    def _register_error_handlers(self) -> None:
        """Register error handlers for this router."""
        # Note: Error handlers are registered at the app level, not router level
        # This is a placeholder for future implementation
        pass


# DEPENDENCY INJECTION PATTERNS
class ModuleDeps:
    """Standard dependencies for a COS module.

    Usage:
    -----
        # Create a dependency factory for the module
        async def get_module_deps(
            request: Request,
            db: Annotated[AsyncSession, Depends(get_async_db)],
            settings: Annotated[Settings, Depends(get_settings)],
            background_tasks: BackgroundTasks,
        ) -> ModuleDeps:
            return ModuleDeps(
                module=ModuleLabel.TECH_CC,
                request=request,
                db=db,
                settings=settings,
                background_tasks=background_tasks,
                request_id=get_request_id(),
            )

        @router.get("/items")
        async def get_items(
            deps: Annotated[ModuleDeps, Depends(get_module_deps)],
        ):
            # Access db, settings, etc. through deps

    """

    def __init__(
        self,
        module: ModuleLabel,
        request: Request | None = None,
        db: AsyncSession | None = None,
        settings: Settings | None = None,
        background_tasks: BackgroundTasks | None = None,
        request_id: str | None = None,
    ) -> None:
        self.module = module
        self.request = request
        self.db = db
        self.settings = settings
        self.background_tasks = background_tasks
        self.request_id = request_id


# TESTING UTILITIES
class RouterTestClient:
    """Test client with dependency override support.

    Usage:
    -----
        async with RouterTestClient(router) as client:
            response = await client.get("/users")
            assert response.status_code == 200

    """

    def __init__(self, router: APIRouter, overrides: dict[Any, Any] | None = None):
        self.router = router
        self.overrides = overrides or {}

    async def __aenter__(self) -> "RouterTestClient":
        from fastapi import FastAPI
        from httpx import AsyncClient

        # Create test app
        self.app = FastAPI()
        self.app.include_router(self.router)

        # Apply dependency overrides
        for dep, override in self.overrides.items():
            self.app.dependency_overrides[dep] = override

        # Create test client
        self.client = AsyncClient(base_url="http://test")
        await self.client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.client.__aexit__(*args)

    # Delegate HTTP methods to client
    def __getattr__(self, name: str) -> Any:
        return getattr(self.client, name)


# PERFORMANCE MONITORING
async def add_performance_headers(request: Request, call_next: Callable[[Request], Any]) -> Any:
    """Middleware to add performance tracking headers."""
    import time

    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time

    response.headers["X-Process-Time"] = f"{process_time:.3f}"
    request_id = get_request_id()
    if request_id:
        response.headers["X-Request-ID"] = request_id

    return response


# USAGE EXAMPLES
"""
# 1. Simple function-based router
from src.backend.cc.services import UserService

router = create_module_router(
    prefix="/users",
    module=ModuleLabel.TECH_CC,
    tags=["users"],
    version="v1",
    rate_limit=RateLimitConfig(requests_per_minute=100),
)

# Create module dependencies factory
async def get_module_deps(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    background_tasks: BackgroundTasks,
) -> ModuleDeps:
    return ModuleDeps(
        module=ModuleLabel.TECH_CC,
        request=request,
        db=db,
        settings=settings,
        background_tasks=background_tasks,
        request_id=get_request_id(),
    )

@router.get("/", response_model=list[UserResponse])
async def list_users(
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[UserService, Depends(get_user_service)],
    deps: Annotated[ModuleDeps, Depends(get_module_deps)],
) -> list[UserResponse]:
    return await service.list_users(
        deps.db,
        limit=pagination.limit,
        offset=pagination.offset
    )


# 2. Class-based router
class UserRouter(BaseRouter):
    prefix = "/users"
    tags = ["users", "authentication"]
    module = ModuleLabel.TECH_CC
    version = "v1"
    rate_limit = RateLimitConfig(requests_per_minute=100)

    def __init__(self, service: UserService):
        self.service = service
        super().__init__()

    def _register_routes(self) -> None:
        # Create module deps factory for this router
        async def get_module_deps(
            request: Request,
            db: Annotated[AsyncSession, Depends(get_async_db)],
            settings: Annotated[Settings, Depends(get_settings)],
            background_tasks: BackgroundTasks,
        ) -> ModuleDeps:
            return ModuleDeps(
                module=self.module,
                request=request,
                db=db,
                settings=settings,
                background_tasks=background_tasks,
                request_id=get_request_id(),
            )

        @self.router.get("/", response_model=list[UserResponse])
        async def list_users(
            pagination: Annotated[PaginationParams, Depends()],
            deps: Annotated[ModuleDeps, Depends(get_module_deps)],
        ) -> list[UserResponse]:
            return await self.service.list_users(
                deps.db,
                limit=pagination.limit,
                offset=pagination.offset
            )

        @self.router.get("/{user_id}", response_model=UserResponse)
        async def get_user(
            user_id: int,
            deps: Annotated[ModuleDeps, Depends(get_module_deps)],
        ) -> UserResponse:
            user = await self.service.get_user(deps.db, user_id)
            if not user:
                raise NotFoundError("User", user_id)
            return user

        @self.router.post("/", response_model=UserResponse, status_code=201)
        async def create_user(
            data: UserCreate,
            deps: Annotated[ModuleDeps, Depends(get_module_deps)],
        ) -> UserResponse:
            # Publish event in background
            deps.background_tasks.add_task(
                publish_event,
                "user.created",
                {"user_id": user.id}
            )
            return await self.service.create_user(deps.db, data)


# 3. Testing example
async def test_list_users():
    # Mock dependencies
    mock_service = AsyncMock(spec=UserService)
    mock_service.list_users.return_value = [
        UserResponse(id=1, name="Test User")
    ]

    # Create router with mocked service
    router = UserRouter(mock_service)

    # Test with client
    async with RouterTestClient(
        router.router,
        overrides={get_user_service: lambda: mock_service}
    ) as client:
        response = await client.get("/v1/users?page=1&limit=10")
        assert response.status_code == 200
        assert len(response.json()) == 1
"""

# MIGRATION GUIDE
"""
To migrate existing routers:

1. Replace direct APIRouter() with create_module_router()
2. Add module label and version
3. Convert to Annotated[Type, Depends()] pattern
4. Add standard error handlers
5. Implement rate limiting where needed
6. Add performance monitoring
7. Update tests to use RouterTestClient

Example migration:
# Before:
router = APIRouter(prefix="/users", tags=["users"])

# After:
router = create_module_router(
    prefix="/users",
    module=ModuleLabel.TECH_CC,
    tags=["users"],
    version="v1",
    rate_limit=RateLimitConfig(requests_per_minute=100)
)
"""

# CHECKLIST FOR NEW ROUTERS
"""
□ Use create_module_router() factory
□ Set appropriate module label
□ Define API version
□ Configure rate limiting
□ Use Annotated dependencies
□ Add OpenAPI documentation
□ Handle all error cases
□ Include request ID in responses
□ Add performance metrics
□ Write comprehensive tests
□ Document breaking changes
□ Plan deprecation strategy
"""

# TODO: Future enhancements
# - WebSocket support patterns
# - GraphQL integration
# - gRPC gateway patterns
# - API versioning automation
# - OpenAPI schema validation
# - Contract testing utilities
