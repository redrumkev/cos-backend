#!/bin/bash
# CI Check Script - Runs all quality gates in sequence
# This script simulates the CI pipeline locally

set -e  # Exit on any error

echo "🚀 Starting CI Quality Gates Check..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 1. Install dependencies
echo "📦 Installing dependencies..."
uv pip sync -e ".[dev]"
print_status "Dependencies installed"

# 2. Run pre-commit hooks
echo "🔍 Running pre-commit hooks..."
pre-commit run --all-files
print_status "Pre-commit hooks passed"

# 3. Run tests with coverage
echo "🧪 Running tests with coverage..."
# Use environment variable for coverage threshold, default to 97 for CI
COVERAGE_THRESHOLD=${COVERAGE_FAIL_UNDER:-97}
pytest -q --cov=src --cov-report=term --cov-report=html --cov-fail-under=${COVERAGE_THRESHOLD}
print_status "Tests passed with ${COVERAGE_THRESHOLD}% coverage"

# 4. Run mypy type checking
echo "🔍 Running mypy type checking..."
mypy .
print_status "Type checking passed"

# 5. Final success message
echo ""
print_status "All CI quality gates passed! 🎉"
echo "Coverage report available in htmlcov/index.html"
