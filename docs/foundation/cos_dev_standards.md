# COS Development Standards v1.0
**Purpose:** Non-negotiable standards for all COS code.

## I. Test-Driven Development Workflow

### The TDD Cycle
1. **RED**: Write a failing test first (defines the specification)
2. **GREEN**: Write minimal code to make the test pass
3. **REFACTOR**: Improve code while keeping tests green

### Test Coverage Requirements
- Minimum 95% code coverage required
- Unit tests for all functions and classes
- Integration tests for component interactions
- API tests for all endpoints
- Edge case tests for error conditions
- Performance tests for critical paths

### Test Best Practices
- One logical assertion per test
- Descriptive test names (test_should_do_something_when_condition)
- Use fixtures for common setup
- Mock external dependencies
- Test both success and failure paths

## II. Code Quality Standards

### Typing and Validation
- All function parameters and returns must be typed
- Pydantic for all data validation and schemas
- Mypy with strict mode enabled
- Type annotations for variables when not obvious

### Style and Formatting
- Black for code formatting
- Ruff for linting
- isort for import organization
- Maximum line length: 88 characters
- Consistent naming patterns:
  - snake_case for variables and functions
  - PascalCase for classes
  - UPPER_CASE for constants

### Documentation
- Docstrings for all public functions and classes
- Clear purpose statements at the top of files
- Comments only for complex logic, not obvious code
- Explicit TODO markers must include ticket numbers

## III. "Mama Bear" Logging System

### Success Logging
- Minimal green logs for successful operations
- Timing information for performance tracking
- Structured format for machine readability

### Error Logging
- All errors must include:
  - What: Error type and message
  - When: Timestamp
  - Where: Module, function, line number
  - Context: Relevant state information
  - Suggestion: Possible remediation

### Log Levels
- ERROR: Unexpected failures requiring attention
- WARNING: Potential issues or edge conditions
- INFO: Key lifecycle events only
- DEBUG: Detailed information (development only)

## IV. Database Practices

### Schema Management
- Each module has its own schema
- Dynamic schema binding via config.settings
- Explicit schema references in table definitions
- Alembic for migrations

### Query Optimization
- Limit queries to necessary fields
- Use joins instead of N+1 queries
- Batch operations for bulk processing
- Index frequently queried columns

### Transaction Management
- Explicit transaction boundaries
- Proper error handling and rollback
- Use SQLAlchemy session management consistently

## V. Error Handling

### Exception Hierarchy
- Use custom exception classes for domain errors
- Categorize exceptions by type and severity
- Map exceptions to HTTP status codes consistently

### Error Responses
- Consistent error response format:
  ```json
  {
    "error": "Error type",
    "message": "Human-readable message",
    "details": {"field": "Specific error"}
  }

- Detailed validation errors for client inputs
- Safe error messages (no sensitive data)

### Recovery Strategies

- Retry mechanisms for transient failures
- Circuit breakers for external dependencies
- Graceful degradation for non-critical features

## VI. Security Practices
### Authentication & Authorization

- Token-based authentication
- Role-based access control
- Principle of least privilege
 Input validation on all endpoints

### Data Protection

- No secrets in code or logs
- Environment variables for sensitive configuration
- Proper encryption for sensitive data
- Sanitize all user inputs

### Dependency Management

- Regular security scanning
- Dependency pinning for reproducibility
- Vulnerability tracking and remediation

## VII. Performance Standards
### Response Time

- API endpoints should respond in <300ms
- Background operations should be asynchronous
- Progress indication for long-running operations

### Resource Utilization

- Efficient memory usage
- Connection pooling for databases
- Caching for expensive operations
- Pagination for large result sets

### Scalability Patterns

- Stateless design where possible
- Horizontal scaling support
- Asynchronous processing for intensive operations
