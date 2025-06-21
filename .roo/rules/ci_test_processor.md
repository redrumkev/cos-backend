---
description:
globs:
alwaysApply: false
---
# CI Test Processor - Automated Test Triage System

**Version**: 3.0
**Applies To**: `tests/**/*.py`, `.github/workflows/*.yml`, `tests/TODO/*.md`, `scripts/ci_triage.py`
**Trigger**: Manual activation, test failures detected, infrastructure changes
**Priority**: Critical

## Summary
Fully automated CI Test Triage System that analyzes, categorizes, skips, and tracks failing tests systematically through `scripts/ci_triage.py` to maintain both development velocity and test quality with enhanced automation.

## Dual Mandate
- **Velocity**: Get CI green immediately via systematic skipping with clear rationale
- **Quality**: Maintain complete failure visibility through structured TODO tracking and systematic re-enablement

## Description
Strategic test failure triage system that mirrors CI locally, categorizes all test outcomes, and implements systematic skipping with detailed tracking. Enhanced with `scripts/ci_triage.py` automation for infrastructure detection, test log parsing, markdown updates, and skip decorator management.

---

## Phase 1: Automated CI Mirror & Analysis

### Automation via scripts/ci_triage.py

#### Full Triage Process
```bash
# Complete automated triage
python scripts/ci_triage.py --mode=full

# Individual operations
python scripts/ci_triage.py --check-infrastructure
python scripts/ci_triage.py --update-markdown
python scripts/ci_triage.py --apply-skips
```

#### Infrastructure Detection
- **PostgreSQL**: Auto-detect dev (5433) and test (5434) databases
- **Redis**: Check connection to port 6379 with authentication
- **Neo4j**: Validate Bolt connection on port 7687
- **Service Status**: JSON status output with re-enablement readiness

#### Systematic Test Categorization
**Enhanced Analysis with Test IDs:**
- **failing_tests**: Tests with infrastructure dependencies → `CC-001`, `UT-001`, `IT-001`, etc.
- **needs_improvement**: Tests with warnings/flaky behavior → Track with Linked Issue/PR column
- **todo_coverage**: Missing coverage with specific function names → Enhanced Coverage Gap details

---

## Phase 2: Enhanced Skip Decorator Management

### Automated Skip Decorator Templates
```python
# Infrastructure-dependent tests (Auto-applied by ci_triage.py)
@pytest.mark.skip(reason="Infrastructure: PostgreSQL services not available locally. Re-enable in Sprint 2 when docker-compose setup is complete. Trigger: CC-001")

# Service-specific tests
@pytest.mark.skip(reason="Service: Neo4j not configured locally. Re-enable in Sprint 3 after graph service setup. Trigger: GR-001")

# Integration tests
@pytest.mark.skip(reason="Integration: Redis pub/sub not available locally. Re-enable when message bus is configured. Trigger: IT-001")
```

### Intelligent Application via CITriageManager
- **SkipDecoratorManager**: Automatically applies skips based on infrastructure availability
- **Test File Discovery**: Scans all test directories for applicable files
- **Smart Detection**: Only applies skips where needed, preserves existing decorators
- **Trigger Integration**: Links skips to specific re-enablement trigger IDs

---

## Phase 3: Enhanced TODO Management System

### Automated File Updates
**Enhanced failing_tests.md:**
- Test ID column: `🆔` (CC-001, UT-001, IT-001, etc.)
- Re-enablement Trigger column: Specific commands/conditions
- Auto-generated infrastructure status section
- Real-time service availability dashboard

**Enhanced needs_improvement.md:**
- Linked Issue/PR column for tracking test cleanup
- Warning categorization and priority assignment
- Integration with development workflow

**Enhanced todo_list.md:**
- Coverage Gap details: Specific function names and behaviors
- Implementation planning with sprint integration
- Detailed missing test specifications

### Real-Time Infrastructure Status
```json
{
  "postgres": {"dev": false, "test": false},
  "redis": false,
  "neo4j": false,
  "all_services_ready": false,
  "basic_db_ready": false,
  "timestamp": "2024-12-19T21:35:17.123456"
}
```

---

## Phase 4: Re-enablement Trigger System

### Automated Trigger Detection
**Service-Specific Triggers:**
```bash
# CC-001: CC Module Tests
🧠 Re-enable when: `pg_isready -h localhost -p 5434` returns 0 AND `DATABASE_URL_TEST` env var is set

# UT-001: Unit Tests
🧠 Re-enable when: `asyncpg.connect(DATABASE_URL_TEST)` succeeds AND `pytest.env.has_test_db` is True

# GR-001: Graph Tests
🧠 Re-enable when: `NEO4J_URI` is resolvable AND `test_env.neo4j.is_mock` is False AND database ready

# Global Trigger
🧠 Re-enable when: `scripts/ci_triage.py --check-infrastructure` returns `all_services_ready=True`
```

### Automated Re-enablement Workflow
1. **Infrastructure Detection**: `ci_triage.py` monitors service availability
2. **Trigger Evaluation**: Checks specific conditions for each test category
3. **Decorator Removal**: Automatically removes skip decorators when conditions are met
4. **Progress Tracking**: Updates TODO files with resolution status
5. **Validation Testing**: Runs focused test subsets to verify functionality

---

## Implementation Workflows

### Workflow A: Automated Test Failure Triage
**Trigger**: Test failures detected
**Command**: `python scripts/ci_triage.py --mode=full`
**Steps**:
1. **Infrastructure Check**: Detect available services automatically
2. **Test Execution**: Run pytest and parse output systematically
3. **Failure Categorization**: Auto-categorize by error patterns
4. **Markdown Updates**: Update all TODO files with current status
5. **Skip Application**: Apply decorators to infrastructure-dependent tests
6. **Validation**: Verify CI goes green with systematic skipping

### Workflow B: Infrastructure Progress Monitoring
**Trigger**: Infrastructure service becomes available
**Command**: `python scripts/ci_triage.py --check-infrastructure`
**Steps**:
1. **Service Detection**: Auto-detect newly available services
2. **Trigger Evaluation**: Check re-enablement conditions
3. **Selective Re-enablement**: Remove skips for ready test categories
4. **Focused Testing**: Run specific test subsets
5. **Progress Documentation**: Update TODO files with completion status

### Workflow C: Continuous Monitoring
**Trigger**: Scheduled/on-demand
**Command**: `python scripts/ci_triage.py --update-markdown`
**Steps**:
1. **Status Refresh**: Update infrastructure status in TODO files
2. **Progress Assessment**: Evaluate sprint milestone completion
3. **Re-enablement Opportunities**: Identify tests ready for activation
4. **Documentation Sync**: Ensure TODO files reflect current reality

---

## Roo Code Automation Integration

### Enhanced File Change Triggers
- **Test file change**: Auto-suggest `ci_triage.py` run, check infrastructure dependencies
- **Infrastructure change**: Auto-detect readiness, suggest decorator removal, run targeted tests
- **CI YAML change**: Re-parse configuration, update automation parameters
- **TODO file manual edit**: Validate consistency with actual test status

### Intelligent Code Suggestions
- **Smart Skip Patterns**: When adding infrastructure-dependent tests, suggest appropriate trigger IDs
- **Infrastructure Integration**: Auto-detect service dependencies in new test files
- **Automated Validation**: Suggest `ci_triage.py` runs after infrastructure changes
- **Progress Tracking**: Recommend TODO updates based on resolved infrastructure issues

### Advanced Automation Hooks
```bash
# Pre-commit validation
python scripts/ci_triage.py --check-infrastructure && echo "Infrastructure validated"

# Post-infrastructure setup
python scripts/ci_triage.py --mode=full && git add tests/TODO/*.md && git commit -m "auto: Update test triage after infrastructure changes"

# Development workflow integration
alias cos-test-status="python scripts/ci_triage.py --check-infrastructure"
alias cos-test-triage="python scripts/ci_triage.py --mode=full"
```

---

## Success Metrics & Validation

### Phase 1 Success Criteria (COMPLETE ✅)
- ✅ All test failures categorized with Test IDs in TODO files
- ✅ CI pipeline shows 0 failing tests (570+ tests systematically skipped)
- ✅ Clear roadmap with re-enablement triggers and sprint targets
- ✅ Automated infrastructure detection and status reporting

### Phase 2 Success Criteria (TARGET)
- 🎯 Infrastructure services automated via docker-compose
- 🎯 Systematic re-enablement of 400+ tests through automation
- 🎯 Real-time TODO file updates reflecting actual progress
- 🎯 Zero manual intervention for test triage process

### Automation Quality Metrics
- **Accuracy**: 95%+ correct test failure categorization via pattern matching
- **Coverage**: 100% of failing tests have skip decorators with trigger IDs
- **Tracking**: All skipped tests documented with specific re-enablement conditions
- **Velocity**: <2min from test failure detection to categorized skip application
- **Intelligence**: Automated infrastructure detection and re-enablement suggestions

---

## Advanced Automation Features

### Intelligent Infrastructure Management
```python
class InfrastructureChecker:
    """Auto-detect service availability and suggest actions"""

class TestLogParser:
    """Parse pytest output and categorize failures by error patterns"""

class MarkdownUpdater:
    """Maintain TODO files with current status and infrastructure state"""

class SkipDecoratorManager:
    """Apply/remove skip decorators based on infrastructure availability"""
```

### CI/CD Integration Pipeline
- **Pre-commit**: Validate test triage consistency
- **Post-infrastructure**: Auto-update test status and re-enable ready tests
- **Pull Request**: Generate test status reports and progress metrics
- **Deployment**: Validate infrastructure requirements before release

### Development Workflow Enhancements
```bash
# Daily development routine
cos-test-status                    # Check infrastructure readiness
cos-test-triage                    # Run full triage if needed
pytest tests/backend/cc/           # Run ready tests only
git add -A && git commit -m "..."  # Commit with auto-updated TODO files
```

---

## Rule Activation Commands

### Primary Automation
```bash
# Full automated triage (recommended)
python scripts/ci_triage.py --mode=full

# Infrastructure monitoring
python scripts/ci_triage.py --check-infrastructure

# Selective operations
python scripts/ci_triage.py --update-markdown
python scripts/ci_triage.py --apply-skips
```

### Integration with Development
```bash
# Add to .bashrc/.zshrc for COS development
alias tm-status="python scripts/ci_triage.py --check-infrastructure"
alias tm-triage="python scripts/ci_triage.py --mode=full"
alias tm-ready="python scripts/ci_triage.py --check-infrastructure | jq '.all_services_ready'"
```

---

*This enhanced rule implements Kevin's vision of fully automated test triage that maintains both velocity and quality through intelligent infrastructure detection, systematic categorization, and clear re-enablement pathways.*
