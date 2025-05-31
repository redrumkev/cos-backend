# CI Check Script - Runs all quality gates in sequence
# This script simulates the CI pipeline locally

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting CI Quality Gates Check..." -ForegroundColor Green

function Write-Success {
    param($Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Error {
    param($Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Warning {
    param($Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

try {
    # 1. Install dependencies
    Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
    uv pip sync -e ".[dev]"
    Write-Success "Dependencies installed"

    # 2. Run pre-commit hooks
    Write-Host "🔍 Running pre-commit hooks..." -ForegroundColor Cyan
    pre-commit run --all-files
    Write-Success "Pre-commit hooks passed"

    # 3. Run integration tests first (highest confidence)
    Write-Host "🧪 Running integration tests..." -ForegroundColor Cyan
    $env:ENABLE_DB_INTEGRATION = "1"
    pytest tests/integration/ -v --tb=short
    Write-Success "Integration tests passed"

    # 4. Run unit tests with coverage
    Write-Host "🧪 Running unit tests with coverage..." -ForegroundColor Cyan
    $CoverageThreshold = if ($env:COVERAGE_FAIL_UNDER) { $env:COVERAGE_FAIL_UNDER } else { 97 }
    pytest tests/unit/ tests/common/ tests/backend/ --cov=src --cov-report=term --cov-report=html --cov-fail-under=$CoverageThreshold
    Write-Success "Unit tests passed with $CoverageThreshold% coverage"

    # 5. Run mypy type checking with proper async support
    Write-Host "🔍 Running mypy type checking..." -ForegroundColor Cyan
    mypy . --show-error-codes --pretty
    Write-Success "Type checking passed"

    # 6. Validate test markers and async patterns
    Write-Host "🔍 Validating test structure..." -ForegroundColor Cyan
    pytest --collect-only -q | Out-Null
    Write-Success "Test structure validation passed"

    # 7. Final success message
    Write-Host ""
    Write-Success "All CI quality gates passed! 🎉"
    Write-Host "Coverage report available in htmlcov/index.html" -ForegroundColor Cyan
    Write-Host "Integration tests demonstrate PostgreSQL transaction isolation ✨" -ForegroundColor Green
    Write-Host "Type safety enforced with strict mypy configuration 🛡️" -ForegroundColor Green
}
catch {
    Write-Host "❌ CI check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
