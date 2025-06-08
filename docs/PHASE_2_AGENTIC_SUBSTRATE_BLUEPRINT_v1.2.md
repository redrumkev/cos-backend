# COS Phase 2: Agentic Substrate & .taskmaster Workflow v1.2

**Document Type**: Strategic Architecture & Workflow Implementation
**Version**: 1.2 (Updated June 8, 2025)
**Date**: June 8, 2025
**Lead Visionary**: Kevin
**Status**: Living Document - Updated Throughout Phase 2

---

## Workflow Evolution: Claude-to-Cursor .taskmaster Pattern

### Context & Vision

Phase 2 introduces a revolutionary development workflow where Claude (on Windows 11/WSL) provides strategic direction and task breakdown, while Cursor (on Mac) executes specific implementation tasks using fresh context windows and MCP-powered tools.

**Core Philosophy**: Each task gets a pristine context window with precise, up-to-date context and agentic execution capabilities that meet or exceed the dual mandate (100% quality, 100% efficiency).

### .taskmaster Task Structure

#### Directory Structure
```
.taskmaster/
├── tasks/
│   ├── task_001.txt       # First implementation task
│   ├── task_002.txt       # Second implementation task
│   ├── task_00n.txt       # Nth implementation task
├── completed/
│   ├── task_001_completed.md  # Completion report
│   └── task_002_completed.md
└── templates/
    ├── step_0_template.md    # Standard step 0 instructions
    └── task_template.md      # Standard task format
```

#### Standard Task Format (.txt)

```markdown
# Task ID: task_001
# Sprint: 2.1 - Database Foundation
# Priority: HIGH
# Estimated Duration: 2-4 hours
# Dependencies: Phase 1 CI completion

## Task Title
Implement MCP Tools Foundation with L1 Memory Layer Integration

## Context Requirements
Step 0: Load precise context via MCP calls

### Step 0.1: Context7 MCP Calls (REQUIRED)
```bash
# Load current project context
context7://fastapi/latest
context7://sqlalchemy/2.0
context7://pydantic/v2
context7://pytest/latest
context7://mcp-protocol/latest
```

### Step 0.2: Perplexity AI Research (IF NEEDED)
- Query: "MCP Model Context Protocol implementation patterns for FastAPI"
- Query: "SQLAlchemy 2.0 async session management best practices"

### Step 0.3: Sequential Thinking (IF COMPLEX)
- Use mcp__sequentialthinking__sequentialthinking for complex architectural decisions
- Break down multi-step implementations

### Step 0.4: Tavily Search (IF CURRENT INFO NEEDED)
- Search: "MCP protocol JSON-RPC 2.0 specification updates 2025"
- Search: "FastAPI dependency injection patterns for MCP servers"

## Dual Mandate Requirements
- **Quality**: 97%+ test coverage, zero ruff/mypy errors, comprehensive documentation
- **Efficiency**: Implementation time < 4 hours, reusable patterns, minimal refactoring

## Implementation Requirements

### Primary Objectives
1. Create `src/backend/cc/mcp/` directory structure
2. Implement basic MCP server (`server.py`)
3. Create first MCP tool: `get_system_health`
4. Add L1 memory integration for tool calls
5. Ensure all operations logged to mem0_cc schema

### Technical Specifications
- Follow existing cc module patterns exactly
- Use async/await throughout
- Implement proper error handling with Rich logging
- Add comprehensive type hints
- Create corresponding test files with 97%+ coverage

### Acceptance Criteria
- [ ] MCP server responds to capabilities request
- [ ] get_system_health tool functional via MCP
- [ ] All tool calls logged to mem0_cc.events table
- [ ] Tests achieve 97%+ coverage
- [ ] Pre-commit hooks pass (ruff, mypy, bandit)
- [ ] Integration test demonstrates end-to-end MCP flow

## Files to Create/Modify
```
src/backend/cc/mcp/__init__.py
src/backend/cc/mcp/server.py
src/backend/cc/mcp/tools/__init__.py
src/backend/cc/mcp/tools/health_tools.py
tests/backend/cc/mcp/test_server.py
tests/backend/cc/mcp/tools/test_health_tools.py
```

## Success Metrics
- Implementation time: < 4 hours
- Test coverage: 97%+
- Zero lint/type errors
- MCP compliance validated
- Documentation complete

## Completion Criteria
- All acceptance criteria met
- Claude review and approval
- MCP server fully functional
- Ready for task_002 (MCP Resources)

## Next Task Preparation
- Identify patterns for task_002 (MCP Resources implementation)
- Document any architecture decisions for future tasks
- Update Sprint 2.1 progress tracking
```

#### Step 0 Template (Standardized Cursor Instructions)

```markdown
# Step 0: Context Loading & Preparation

You are Cursor AI working on the COS (Creative Operating System) Phase 2 implementation. This is a fresh context window for a specific .taskmaster task.

## CRITICAL INSTRUCTIONS

### 1. Load Current Context (REQUIRED)
Execute these MCP calls immediately:
```bash
# Load precise technical context
context7://fastapi/latest
context7://sqlalchemy/2.0
context7://pydantic/v2
context7://pytest/latest
context7://mcp-protocol/latest
```

### 2. Advanced Research Tools (USE AS NEEDED)
- **For cutting-edge info**: Use mcp__perplexity__perplexity_search_web
- **For complex decisions**: Use mcp__sequentialthinking__sequentialthinking
- **For comprehensive search**: Use mcp__tavily__tavily-search

### 3. Project Context (READ FIRST)
- Current working directory: `/path/to/cos/`
- Branch: `feat/cc-goldPh2`
- Phase: 2.1 Database Foundation
- Architecture: Hybrid Vertical Slice + Atomic Composition
- Test Coverage Requirement: 97%+
- Code Quality: Zero ruff/mypy errors

### 4. Dual Mandate (NEVER COMPROMISE)
- **100% Quality**: Enterprise-grade code, comprehensive tests, full documentation
- **100% Efficiency**: Fast implementation, reusable patterns, minimal iteration

### 5. Implementation Standards
- Use existing `cc` module patterns exactly
- Follow async/await throughout
- Rich logging for all errors
- Comprehensive type hints
- Test-driven development (RED → GREEN → REFACTOR)

### 6. Success Criteria
Every task must:
- [ ] Achieve 97%+ test coverage
- [ ] Pass all pre-commit hooks (ruff, mypy, bandit)
- [ ] Include comprehensive documentation
- [ ] Complete within estimated timeframe
- [ ] Be ready for immediate integration

### 7. Completion Protocol
When task is complete:
- Run full quality checks
- Generate completion report
- Close MCP connections
- End context window

## Ready to Begin
You have everything needed to execute this task to perfection. Follow the dual mandate, use the loaded context, and deliver gold-standard results.
```

---

## Phase 2 Sprint Roadmap with .taskmaster Integration

### Sprint 2.1: Database Foundation (Week 1)
**Tasks**: task_001 → task_005

| Task | Focus | Duration | Dependencies |
|------|-------|----------|--------------|
| task_001 | MCP Tools Foundation | 4h | Phase 1 complete |
| task_002 | MCP Resources Layer | 3h | task_001 |
| task_003 | L1 Memory Schema | 2h | task_001 |
| task_004 | Logfire Integration | 3h | task_003 |
| task_005 | Sprint Integration Tests | 2h | task_001-004 |

**Coverage Progression**: 30% → 45% (Re-enable P2-ASYNC-001, P2-SCHEMA-001, P2-MODELS-001)

### Sprint 2.2: Application Layer (Week 2)
**Tasks**: task_006 → task_010

| Task | Focus | Duration | Dependencies |
|------|-------|----------|--------------|
| task_006 | Redis Pub/Sub Client | 3h | Sprint 2.1 |
| task_007 | Event Publishing Layer | 2h | task_006 |
| task_008 | Cross-Module Communication | 4h | task_007 |
| task_009 | Service Layer Enhancement | 3h | task_007 |
| task_010 | Sprint Integration Tests | 2h | task_006-009 |

**Coverage Progression**: 45% → 65% (Re-enable P2-MEM0-001, P2-ROUTER-001, P2-SERVICE-001)

### Sprint 2.3: Graph Layer (Week 3)
**Tasks**: task_011 → task_014

| Task | Focus | Duration | Dependencies |
|------|-------|----------|--------------|
| task_011 | L1→L2 Consumer Service | 4h | Sprint 2.2 |
| task_012 | Neo4j Graph Models | 3h | task_011 |
| task_013 | Semantic Transformation | 4h | task_012 |
| task_014 | Sprint Integration Tests | 2h | task_011-013 |

**Coverage Progression**: 65% → 80% (Re-enable P2-GRAPH-001)

### Sprint 2.4: Integration & Polish (Week 4)
**Tasks**: task_015 → task_018

| Task | Focus | Duration | Dependencies |
|------|-------|----------|--------------|
| task_015 | Full Stack Integration | 4h | Sprint 2.3 |
| task_016 | AlphaEvolve PoC | 5h | task_015 |
| task_017 | Documentation & Polish | 3h | task_015 |
| task_018 | Final Integration Tests | 2h | task_015-017 |

**Coverage Progression**: 80% → 97% (Re-enable P2-INTEGRATION-001)

---

## Iterative Feedback Loop Process

### Claude (Strategic Oversight) ↔ Cursor (Implementation)

#### 1. Task Creation (Claude)
```python
# Claude creates task_00n.txt with:
- Precise context requirements
- Step 0 MCP loading instructions
- Clear acceptance criteria
- Dual mandate alignment
- Time estimates
```

#### 2. Context Loading (Cursor)
```bash
# Cursor executes Step 0:
context7://fastapi/latest          # Load current FastAPI patterns
context7://sqlalchemy/2.0         # Load SQLAlchemy 2.0 async patterns
perplexity_search("MCP JSON-RPC")  # Research if needed
sequential_thinking()              # Break down complex decisions
```

#### 3. Implementation (Cursor)
- Fresh context window with precise information
- Agentic execution using loaded context
- Real-time problem solving with MCP tools
- Continuous quality validation

#### 4. Review & Feedback (Claude)
```python
# Claude reviews:
- Implementation quality
- Architecture alignment
- Test coverage results
- Performance metrics
- Preparation for next task
```

#### 5. Task Closure (Both)
```python
# Cursor generates completion report
# Claude validates completion
# MCP connections closed
# Context window ended
# Next task prepared
```

### Mid-Task Course Correction

**If Cursor gets "into the weeds" or loses direction:**
1. **Immediate Reset**: Close current context window
2. **Claude Assessment**: Analyze what went wrong
3. **Task Refinement**: Update task_00n.txt with clearer guidance
4. **Fresh Start**: New context window with improved Step 0 instructions
5. **Forward Progress**: Resume with better clarity

---

## MCP Integration Architecture

### Core MCP Components (from v1.1)

#### Tools (Action Layer)
```yaml
# src/backend/cc/mcp/tools/health_tools.yaml
name: get_system_health
description: "Retrieve comprehensive system health across all modules"
parameters:
  include_traces:
    type: boolean
    description: "Include recent Logfire trace summaries"
  time_window:
    type: string
    description: "Time window for health data (1h, 24h, 7d)"
    default: "1h"
```

#### Resources (Data Layer)
```yaml
# src/backend/cc/mcp/resources/system_state.yaml
name: system_state
uri: "state://cc/current"
description: "Live system state for CC module"
mime_type: "application/json"
access_pattern: "read-only"
```

#### Prompts (Guidance Layer)
```yaml
# src/backend/cc/mcp/prompts/diagnostic_prompts.yaml
name: system_diagnostic
description: "Guide agent through comprehensive system analysis"
template: |
  You are analyzing the COS system health. Use these steps:
  1. Call get_system_health(include_traces=true)
  2. Check system_state resource for any misconfigurations
  3. Identify top 3 optimization opportunities
```

### Memory Layer Integration (L1→L2→L3→L4)

#### L1: Postgres (`mem0_cc`) - Raw Event Storage
```sql
-- All MCP tool calls logged here
CREATE TABLE mem0_cc.events (
    id UUID PRIMARY KEY,
    tool_name VARCHAR(100) NOT NULL,
    parameters JSONB,
    result JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    trace_id VARCHAR(100),
    user_id VARCHAR(100)
);
```

#### L1.5: Redis Pub/Sub - Real-Time Distribution
```python
# Every MCP tool call publishes:
redis_client.publish(
    "mcp.tool_called.cc",
    {
        "tool": "get_system_health",
        "result": {...},
        "timestamp": "2025-06-08T12:00:00Z"
    }
)
```

#### L2: Neo4j Graph (`mem0g`) - Semantic Memory
```cypher
// Tool usage patterns become semantic relationships
CREATE (t:Tool:CC {name: "get_system_health"})
CREATE (m:Module:CC {name: "cc"})
CREATE (t)-[:MONITORS]->(m)
```

---

## Success Metrics & Quality Gates

### Per-Task Quality Gates
- **Test Coverage**: ≥97% (automated check)
- **Code Quality**: Zero ruff/mypy errors (pre-commit gates)
- **Performance**: API response times <300ms P95
- **Documentation**: Auto-generated and comprehensive
- **MCP Compliance**: Validated via automated testing

### Sprint Completion Criteria
- **All Tasks Complete**: 100% of planned tasks finished
- **Coverage Increase**: Sprint target achieved (e.g., 30%→45%)
- **Integration Tests**: Full end-to-end functionality validated
- **Architecture Review**: Claude approval of implementation quality
- **Readiness Check**: Next sprint can begin immediately

### Phase 2 Ultimate Success
- **97% Test Coverage**: Permanent CI threshold set
- **Zero Technical Debt**: All P2-XXX-001 triggers resolved
- **MCP Gold Standard**: Full agentic substrate operational
- **Multi-Century Foundation**: Architecture ready for decades of evolution

---

## Risk Mitigation & Workflow Safeguards

### Context Window Management
- **Fresh Start Protocol**: Every task gets clean context
- **Context Overflow Protection**: Automatic task breakdown if context limits approached
- **State Preservation**: Critical information captured in .taskmaster files

### Quality Assurance
- **Dual Review**: Both Claude strategic and Cursor implementation validation
- **Automated Gates**: Pre-commit hooks prevent quality regression
- **Roll-back Strategy**: Any task can be reverted and restarted

### Timeline Protection
- **Time Boxing**: Strict duration limits per task
- **Scope Creep Prevention**: Clear acceptance criteria prevent over-engineering
- **Progress Tracking**: Real-time visibility into sprint progression

---

## Conclusion: Systematic Excellence at Scale

The .taskmaster workflow represents a revolutionary approach to human-AI collaborative development:

- **Systematic**: Every task follows identical patterns for predictable excellence
- **Scalable**: Fresh context windows prevent information decay
- **Quality-First**: Dual mandate ensures no compromise between speed and excellence
- **Future-Proof**: MCP architecture prepares for multi-century evolution

**Next Action**: Create feat/cc-goldPh2 branch and begin task_001 implementation.

---

*This document evolves with each sprint to capture learnings and optimize the workflow for maximum effectiveness.*
