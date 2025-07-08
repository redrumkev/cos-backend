# ADR-002: Living Patterns System

## Status

Accepted

## Context

As the Creative Operating System (COS) evolves towards a multi-module, multi-agent architecture supporting a 100+ book legacy vision, we face critical challenges in maintaining code quality, consistency, and evolvability:

1. **Agent Alignment Challenge**: Multiple AI agents and LLMs contributing code risk divergent implementations based on their training data rather than our specific standards.

2. **Rapid Evolution Requirement**: Python ecosystem, libraries, and best practices evolve quickly. Static documentation becomes outdated, leading to technical debt.

3. **Knowledge Transfer**: Both human developers and AI agents need a single source of truth for "how we build things here" that goes beyond simple style guides.

4. **Quality at Scale**: As we grow from CC module to multiple specialized modules (PEM, AIC, etc.), maintaining consistent quality becomes exponentially harder without systematic patterns.

5. **Research-Driven Development**: Our commitment to best practices requires a systematic way to discover, validate, and propagate improvements across the entire codebase.

Building on ADR-001's Strangler Fig pattern for safe refactoring, we need a complementary system for maintaining and evolving our code standards.

## Decision

We will implement a Living Patterns System with the following components:

### 1. Patterns Directory Structure

Create `/src/core_v2/patterns/` as the canonical repository of code blueprints:

```
patterns/
├── COS_PATTERNS_PHILOSOPHY.md    # Why and how we use patterns
├── README.md                      # Quick reference and index
├── service.py                     # Service class patterns
├── async_handler.py               # FastAPI handler patterns
├── error_handling.py              # Exception patterns
├── dependency_injection.py        # DI patterns
├── model.py                       # Data structure patterns
├── router.py                      # API organization patterns
└── [future patterns as needed]
```

### 2. Pattern Lifecycle

Each pattern follows a rigorous lifecycle:

```
Research → Validate → Document → Adopt → Propagate → Monitor → Evolve
```

- **Research**: Use Context7, Tavily, Perplexity, and leading open source
- **Validate**: Test in isolation with comprehensive examples
- **Document**: Include purpose, usage, testing, and migration notes
- **Adopt**: Update pattern file with version and ADR reference
- **Propagate**: Refactor codebase to match using Strangler Fig approach
- **Monitor**: Track effectiveness through code reviews and metrics
- **Evolve**: Continuously improve based on new discoveries

### 3. Pattern-First Development Mandate

All code development must:
1. Consult `/patterns/` before implementation
2. Follow patterns exactly unless proposing improvements
3. Document deviations with clear justification
4. Propose pattern updates through ADR process

### 4. Agent/LLM Contract

Every AI contributor (Claude, GPT, local models) must:
- Load relevant patterns into context before generating code
- Generate code matching our patterns, not generic training data
- Flag when patterns seem outdated or suboptimal
- Never create new patterns without human approval

### 5. Pattern File Format

Each pattern file contains:
- Version and last update date
- Links to relevant ADRs
- Purpose and use cases
- Anti-patterns to avoid
- Canonical implementation
- Usage examples
- Testing approaches
- Migration notes from previous versions

## Consequences

### Positive Consequences

1. **Consistent Excellence**: Every line of code follows researched best practices.

2. **Accelerated Development**: Developers and agents don't waste time deciding "how to implement X."

3. **Evolutionary Architecture**: Patterns evolve systematically rather than through random drift.

4. **Reduced Code Review Burden**: Reviews focus on business logic rather than implementation style.

5. **AI Alignment**: LLMs produce code matching our standards rather than generic patterns.

6. **Knowledge Preservation**: Best practices are codified and versioned, not lost in team transitions.

7. **Confident Refactoring**: Clear patterns make large-scale refactoring safer and faster.

### Trade-offs and Considerations

1. **Initial Investment**: Creating comprehensive patterns requires upfront research and documentation effort.

2. **Maintenance Overhead**: Patterns must be actively maintained or they become technical debt.

3. **Flexibility Balance**: Must avoid over-rigid patterns that stifle innovation.

4. **Research Burden**: Each pattern update requires thorough investigation.

5. **Propagation Complexity**: Updating patterns across a large codebase requires discipline.

## Implementation Plan

### Phase 1: Foundation (Week 1)
- ✅ Create pattern philosophy document
- ✅ Initialize pattern structure with placeholders
- ✅ Document pattern system in this ADR
- Create COS Constitution working document

### Phase 2: Core Patterns (Weeks 2-3)
- Research and document service patterns
- Create async handler patterns
- Establish error handling patterns
- Define dependency injection patterns

### Phase 3: Infrastructure Patterns (Weeks 3-4)
- Database operation patterns
- Caching patterns
- Event sourcing patterns
- Testing patterns

### Phase 4: Integration (Weeks 4-6)
- Update CLAUDE.md with pattern directives
- Migrate existing code to follow patterns
- Create pattern validation tools
- Establish pattern review process

## Success Metrics

- 100% of new code follows established patterns
- Pattern consultation happens automatically (tool-enforced)
- Time to implement new features decreases by 40%
- Code review comments about style/structure drop by 90%
- AI-generated code requires minimal correction

## Relationship to Other ADRs

- **ADR-001**: Patterns guide how we implement Strangler Fig refactoring
- **Future ADRs**: All architecture decisions will reference/update relevant patterns

## References

- "A Pattern Language" - Christopher Alexander (conceptual inspiration)
- Google's Engineering Practices documentation
- Stripe's internal pattern library (as described in engineering blogs)
- Microsoft's Cloud Design Patterns
- Martin Fowler's Patterns of Enterprise Application Architecture

## Decision Date

2025-07-08

## Decision Makers

- Kevin MBA (Strategist/Visionary)
- Claude Code (Tactical Orchestrator)

## Review Schedule

- Monthly pattern effectiveness review
- Quarterly pattern research sprint
- Annual pattern system architecture review

## Appendix: Pattern Evolution Example

When updating a pattern:

1. Create new ADR documenting the change
2. Update pattern file with new version:
   ```python
   """
   Pattern: Service Class
   Version: 2025-07-15 (Updated from 2025-07-08)
   ADR: ADR-003-async-service-improvements

   Changes:
   - Added connection pooling pattern
   - Improved error handling with circuit breakers
   - Added distributed tracing hooks
   """
   ```
3. Create migration script for existing code
4. Update code module by module maintaining green tests
5. Archive old pattern version for reference
