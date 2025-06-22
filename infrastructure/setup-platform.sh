#!/bin/bash

# COS Infrastructure Platform Setup - macOS
# Configures cross-platform Docker environment for COS development

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 COS Infrastructure Setup - macOS"
echo "======================================="

# Detect platform
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: This script is for macOS only"
    echo "   Use setup-platform.ps1 for Windows"
    exit 1
fi

# Check Docker Desktop
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker Desktop not found"
    echo "   Please install Docker Desktop for Mac"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Error: Docker Desktop not running"
    echo "   Please start Docker Desktop"
    exit 1
fi

echo "✅ Docker Desktop detected and running"

# Create data directories
echo "📁 Creating cos-data directory structure..."
COS_DATA_ROOT="$HOME/cos-data"

# Create all required directories
mkdir -p "$COS_DATA_ROOT"/{postgres,redis,neo4j,elasticsearch}/{prod,dev,logs}

# Set proper permissions
chmod -R 755 "$COS_DATA_ROOT"

# Verify directory structure
if [[ -d "$COS_DATA_ROOT" ]]; then
    echo "✅ Directory structure created: $COS_DATA_ROOT"
    ls -la "$COS_DATA_ROOT"
else
    echo "❌ Failed to create directory structure"
    exit 1
fi

# Copy platform-specific configuration files
echo "⚙️  Configuring platform-specific settings..."

# Copy .env file
if [[ -f "$SCRIPT_DIR/.env.macos" ]]; then
    cp "$SCRIPT_DIR/.env.macos" "$SCRIPT_DIR/.env"
    echo "✅ Environment configuration: .env.macos → .env"
else
    echo "❌ Error: .env.macos not found"
    exit 1
fi

# Copy Docker Compose override
if [[ -f "$SCRIPT_DIR/docker-compose.override.yml.macos" ]]; then
    cp "$SCRIPT_DIR/docker-compose.override.yml.macos" "$SCRIPT_DIR/docker-compose.override.yml"
    echo "✅ Docker Compose override: macos → override"
else
    echo "❌ Error: docker-compose.override.yml.macos not found"
    exit 1
fi

# Validate configuration
echo "🔍 Validating configuration..."

# Check if required compose files exist
REQUIRED_FILES=(
    "docker-compose.yml"
    "docker-compose.traefik.yml"
    "docker-compose.mem0g.yml"
    "docker-compose.override.yml"
    ".env"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$SCRIPT_DIR/$file" ]]; then
        echo "✅ Found: $file"
    else
        echo "❌ Missing: $file"
        exit 1
    fi
done

# Test Docker Compose configuration
echo "🧪 Testing Docker Compose configuration..."
if docker-compose -f "$SCRIPT_DIR/docker-compose.yml" config > /dev/null 2>&1; then
    echo "✅ Docker Compose configuration valid"
else
    echo "❌ Docker Compose configuration invalid"
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" config
    exit 1
fi

echo ""
echo "🎯 Setup Complete!"
echo "=================="
echo "Platform: macOS"
echo "Data Root: $COS_DATA_ROOT"
echo "Configuration: .env (from .env.macos)"
echo "Override: docker-compose.override.yml (from .macos)"
echo ""
echo "Next Steps:"
echo "1. cd $SCRIPT_DIR"
echo "2. docker-compose -f docker-compose.yml -f docker-compose.traefik.yml -f docker-compose.mem0g.yml up -d"
echo "3. Verify services: docker ps"
echo ""
echo "🚀 Ready for COS Phase 2 Sprint 2!"