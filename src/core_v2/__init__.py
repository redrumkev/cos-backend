"""Core V2 package - The next evolution of COS infrastructure.

This package implements the Strangler Fig pattern for gradual migration
of core functionality with enhanced patterns and improved architecture.

Package Structure:
- utils/: Core utilities (logger, config, etc.)
- patterns/: Design patterns and abstractions
- services/: Enhanced service implementations (future)
- middleware/: Enhanced middleware components (future)

Migration Strategy:
Following ADR-001, modules are migrated here with:
1. Enhanced type safety
2. Better async support
3. Improved error handling
4. Cleaner abstractions
"""

__version__ = "0.1.0"
