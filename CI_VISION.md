# CI Evolution Plan

## Current State: GitHub Actions
- **Quick CI**: Unit tests on push (2-3 min)
- **Standard CI**: Full tests on PR (5-10 min)
- **Full CI**: Everything on main/release (10-15 min)

### Recent Fixes (2025-07-08)
- Standardized Redis to NO PASSWORD across all test environments
- Fixed virtual environment setup in workflows
- Adjusted performance thresholds for CI environment

## Future State: Mac Studio M4 Max + GitLab (ETA: ~2 weeks)
### Hardware Advantages
- M4 Max: 14-16 CPU cores vs GitHub's 2 cores
- 128GB RAM vs GitHub's 7GB
- Local NVMe SSD vs network storage
- Zero network latency for services

### Expected Performance
- **Quick CI**: 15-30 seconds (10x faster)
- **Standard CI**: 45-60 seconds (10x faster)
- **Full CI**: 1-2 minutes (10x faster)
- **Overnight Matrix**: Python 3.12, 3.13, 3.14-dev on macOS + Linux

## AI Test Summarizer (Future Enhancement)
### Problem
- Test output can be 1000s of lines
- 50 failures often stem from 1 root cause
- Clogs LLM context window

### Solution
- Small LLM (GPT-4-mini) processes raw output
- Returns condensed format:
  ```
  ✅ 1451 tests passed
  ❌ 3 tests failed:
    - test_redis_latency: Expected <5ms, got 7.2ms
    - Root cause: Missing REDIS_PASSWORD env var
    - Fix: Set REDIS_PASSWORD=""
  ```
- Saves 90% context window space
- Enables faster iteration

## Disaster Recovery Strategy
1. **GitHub** (Remote):
   - Private repository for code backup
   - Automated push on every commit
   - Geographic redundancy

2. **GitLab** (Local):
   - Primary CI/CD platform
   - Runs on Mac Studio
   - Full test matrix capabilities

3. **Time Machine** (Local):
   - Hourly system backups
   - Quick recovery from hardware failures

## CI Tiers
### Current (GitHub Actions)
- `feat/*` → Quick CI (unit tests only)
- `release/*` → Standard CI (full test suite)
- `main` → Validation only (should always pass)

### Future (GitLab on Mac Studio)
Same tier strategy but with:
- Real-time performance metrics (1ms Redis latency)
- Parallel execution across all cores
- Pre-warmed service containers
- AI-powered failure analysis

## Migration Plan
1. Mac Studio arrives → Install GitLab Runner
2. Mirror workflows from GitHub to GitLab
3. Run both in parallel for validation
4. Gradually shift to GitLab as primary
5. Keep GitHub as backup/public interface
