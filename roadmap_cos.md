# COS Roadmap

## Vision & Purpose
COS (Creative Operating System) serves a 100+ book legacy vision, translating life-student insights into a technical foundation for creating classic non-fiction works. Every decision honors the Dual Mandate: 100% Quality + 100% Efficiency.

---

## How to Use This Roadmap

- This roadmap guides agentic and human contributors alike.
- Check off each phase in order—never duplicate a module or consider a step “done” until all gold-standard features and tests are present and passing.
- Every significant pattern/process change must be reflected in `/patterns` and documented in ADRs before global propagation.
- Keep this document concise—compress completed tasks into a single summary line.
- When the journey is complete, convert this to an immutable “This is how COS operates” manual for all future contributors and agents.

---

## Long Arc Plan (Strategic Evolution)

### 1. Re-initialize best-practice review of /common and all backend
- Deep-dive analysis ensuring KISS principle throughout
- Extract reusable patterns during review
- Document in /patterns as canonical blueprints
- Each file researched via Context7, Tavily, Zen MCP, Perplexity
- All major research/refactor work must be cross-documented in the relevant ADR

### 2. Create /patterns folder with canonical blueprints ✓ (DONE)
- Living blueprint system established
- ADR-002 documents pattern philosophy
- Initial patterns: service.py, async_handler.py, error_handling.py

### 3. Research every backend file via Context7/Tavily/Zen ✓ (PATTERNS ENHANCED)
- Pattern infrastructure established (manifest.yaml, versioning, fitness checklist)
- Three core patterns optimized: service.py (-29.7%), async_handler.py (-36.4%), error_handling.py (-15.5%)
- README.md enhanced with canonical examples
- v3.0.0 consolidation plans identified (merge async_handler + error_handling)
- Ready for global propagation phase

### 4. Propagate pattern upgrades globally
- MUST follow TDD micro-iteration workflow (~10 lines test → code → green)
- No major pattern/best practice is adopted until rationale is present in `/patterns` and ADR, and test coverage is verified locally and in CI/CD
- Use propagation process to refine workflow itself
- Strangler Fig pattern for safe migration
- Maintain always-green state throughout

### 5. Create ADRs for all major decisions ✓ (STARTED)
- ADR-001: Strangler Fig refactor strategy (DONE)
- ADR-002: Living Patterns System (DONE)
- ADRs for each pattern evolution (cross-reference code changes and rationale)
- All major decisions/changes must be traceable and explainable in ADR

### 6. Setup multi-environment CI on Mac Studio
- Awaiting Mac Studio M4 Max delivery
- Docker + GitLab with local runners
- Tiered testing: fast unit → integration → multi-OS/perf
- GitHub relegated to backup/disaster recovery only
- Review CI infra quarterly and on major Python release for further improvements

### 7. Convert Claude.md to final declarative statement
- Currently: Active working document with checklists
- Future: Compressed "This is how COS operates"
- References /patterns and ADRs for implementation details
- Becomes immutable operating manual

---

## CC Module Gold Standard Roadmap

### 1. Unblock all tests ✓ (DONE)
- 1451 tests passing, 9 legitimate skips
- 86% coverage achieved
- Foundation for fearless refactoring established

### 2. Core codebase & /common analysis
- Apply patterns to shared utilities first (highest reuse)
- Ensure multi-module readiness before duplication
- Focus on DI patterns, async patterns, error handling

### 3. Pattern folder ✓ (FULLY ENHANCED)
- Living Patterns System infrastructure complete (manifest, versioning, contributing guide)
- Three core patterns optimized with 15-36% line reductions
- Agent-readable blueprints with canonical examples
- Ready for global propagation across modules

### 4. Gold standard features (Must-haves before module duplication)
- **Slack integration**: Inter-module communication
- **MCP folder/logic**: Server/client capability
- **MEM0 optimization**: L1 memory layer integration
- **Minimal auth system**: JWT with YAML enable/disable
- **Real-world test infra**: Beyond pytest mocking

### 5. E2E test harness
- Playwright/Puppeteer for browser automation
- Uvicorn test server management
- Operational testing beyond unit tests
- Catch integration issues unit tests miss

### 6. Module role/MCP evolution
- CC as both MCP server and client
- Define module communication protocols
- Prepare for PEM (Prompt Engineering Module)
- Prepare for AIC (AI Coach Module)

### 7. Stateless/stateful design decisions
- Determine BAML/DSPy placement
- Align with modular vision
- Document in ADR with rationale
- Impact on prompt engineering patterns

### 8. Module structure/Docker
- Validate folder structure for duplication
- Schema-per-module (cc.tables, pem.tables)
- Dockerization for local and cloud
- Production-ready scaling patterns

### 9. Security/auth strategy
- JWT implementation with session management
- YAML switches for dev/prod/public modes
- Must flex for different deployments
- Not afterthought but not over-engineered

### 10. Feature expansion for real use cases
- Plan chat/membership sites (hydroponics, plant care)
- Drive abstraction requirements
- RAG, image upload, user learning features
- Ensure patterns support real-world needs

### 11. Learning loops & continuous improvement
- Logfire observability integration
- AlphaEvolve for self-improvement
- User analytics feeding back to system
- Prevent stagnation through data-driven evolution
- Periodic pattern review (e.g., quarterly or on major Python release) to ensure continued world-class standards

---

## Pattern Adoption Protocol

1. Research candidate improvements (Context7, Tavily, OSS exemplars, ADR history)
2. Document/update in `/patterns`, with version notes and migration tips
3. Log decision and rationale in ADR (cross-reference PR or commit)
4. Propagate to all relevant modules, checking tests (unit, integration, CI)
5. Summarize pattern and impact in Claude.md checklist; compress when done
6. Review quarterly or on major release for further improvements

---

## Completed Pattern Enhancements

### ✅ Living Patterns System Infrastructure
- **Pattern Manifest**: Created manifest.yaml for discovery and metadata
- **Versioning System**: PATTERN_VERSION.md tracks all pattern evolution
- **Contributing Guide**: CONTRIBUTING.md ensures consistent pattern updates
- **Fitness Checklist**: FITNESS_CHECKLIST.md validates pattern quality
- **README Enhancement**: Added canonical examples for each pattern

### ✅ Pattern Optimizations (v2.0.0)
- **service.py**: Reduced 29.7% (607→427 lines) - cleaner service lifecycle
- **async_handler.py**: Reduced 36.4% (884→562 lines) - simplified async patterns
- **error_handling.py**: Reduced 15.5% (1126→952 lines) - streamlined error handling
- **Future v3.0.0**: Identified consolidation opportunity (merge async + error patterns)

## Completed Short-term Work

### ✅ Squash working code/tests to single commit on main
- **Status**: Deferred until Mac Studio + GitLab migration
- **Current**: Relying on local lint/tests exclusively
- **Rationale**: GitHub CI disabled, pure backup mode

### ✅ Simplify CI with minimal thresholds
- **Status**: Complete - CI effectively "turned off"
- **GitHub Actions**: Disabled to avoid flaky failures
- **Local validation**: uv run pre-commit for all checks

### ✅ Implement micro-iteration workflow
- **Status**: Complete - Workflow established and proven
- **Process**: Write ~10 lines failing test → minimal code to pass → refactor
- **Evidence**: Sprint 2 delivered with all tests green
- **Next**: Use pattern propagation to refine further

---

*This roadmap evolves from active checklist → completed summary, documenting the journey from aspiration to operational excellence.*
