# COS Infrastructure Platform Setup - Windows
# Configures cross-platform Docker environment for COS development

param(
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$ProjectRoot = Split-Path $ScriptDir -Parent

Write-Host "🚀 COS Infrastructure Setup - Windows" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# Detect platform
if ($env:OS -ne "Windows_NT") {
    Write-Host "❌ Error: This script is for Windows only" -ForegroundColor Red
    Write-Host "   Use setup-platform.sh for macOS/Linux" -ForegroundColor Yellow
    exit 1
}

# Check Docker Desktop
$dockerExists = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerExists) {
    Write-Host "❌ Error: Docker Desktop not found" -ForegroundColor Red
    Write-Host "   Please install Docker Desktop for Windows" -ForegroundColor Yellow
    exit 1
}

# Test Docker daemon
try {
    docker info | Out-Null
    Write-Host "✅ Docker Desktop detected and running" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Docker Desktop not running" -ForegroundColor Red
    Write-Host "   Please start Docker Desktop" -ForegroundColor Yellow
    exit 1
}

# Create data directories
Write-Host "📁 Creating data directory structure..." -ForegroundColor Yellow

$DataRoots = @{
    "postgres" = "P:\postgres_cos"
    "redis" = "E:\redis_cos_data" 
    "neo4j_data" = "F:\neo4j_cos_data"
    "neo4j_logs" = "F:\neo4j_cos_logs"
    "neo4j_transactions" = "F:\neo4j_cos_transactions"
    "elasticsearch" = "F:\elasticsearch_cos_data"
}

foreach ($service in $DataRoots.GetEnumerator()) {
    $path = $service.Value
    if (-not (Test-Path $path)) {
        try {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
            Write-Host "✅ Created: $path" -ForegroundColor Green
        } catch {
            Write-Host "❌ Failed to create: $path" -ForegroundColor Red
            Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "✅ Exists: $path" -ForegroundColor Green
    }
}

# Copy platform-specific configuration files
Write-Host "⚙️  Configuring platform-specific settings..." -ForegroundColor Yellow

# Copy .env file
$envMacFile = Join-Path $ScriptDir ".env.windows"
$envFile = Join-Path $ScriptDir ".env"

if (Test-Path $envMacFile) {
    Copy-Item $envMacFile $envFile -Force
    Write-Host "✅ Environment configuration: .env.windows → .env" -ForegroundColor Green
} else {
    Write-Host "❌ Error: .env.windows not found" -ForegroundColor Red
    exit 1
}

# Copy Docker Compose override
$overrideSrcFile = Join-Path $ScriptDir "docker-compose.override.yml.windows"
$overrideFile = Join-Path $ScriptDir "docker-compose.override.yml"

if (Test-Path $overrideSrcFile) {
    Copy-Item $overrideSrcFile $overrideFile -Force
    Write-Host "✅ Docker Compose override: windows → override" -ForegroundColor Green
} else {
    Write-Host "❌ Error: docker-compose.override.yml.windows not found" -ForegroundColor Red
    exit 1
}

# Validate configuration
Write-Host "🔍 Validating configuration..." -ForegroundColor Yellow

$RequiredFiles = @(
    "docker-compose.yml",
    "docker-compose.traefik.yml", 
    "docker-compose.mem0g.yml",
    "docker-compose.override.yml",
    ".env"
)

foreach ($file in $RequiredFiles) {
    $filePath = Join-Path $ScriptDir $file
    if (Test-Path $filePath) {
        Write-Host "✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
        exit 1
    }
}

# Test Docker Compose configuration
Write-Host "🧪 Testing Docker Compose configuration..." -ForegroundColor Yellow
try {
    $configTest = docker-compose -f (Join-Path $ScriptDir "docker-compose.yml") config 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker Compose configuration valid" -ForegroundColor Green
    } else {
        throw "Invalid configuration"
    }
} catch {
    Write-Host "❌ Docker Compose configuration invalid" -ForegroundColor Red
    Write-Host $configTest -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "🎯 Setup Complete!" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan
Write-Host "Platform: Windows" -ForegroundColor White
Write-Host "Data Roots:" -ForegroundColor White
foreach ($service in $DataRoots.GetEnumerator()) {
    Write-Host "  $($service.Key): $($service.Value)" -ForegroundColor Gray
}
Write-Host "Configuration: .env (from .env.windows)" -ForegroundColor White
Write-Host "Override: docker-compose.override.yml (from .windows)" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. cd $ScriptDir" -ForegroundColor White
Write-Host "2. docker-compose -f docker-compose.yml -f docker-compose.traefik.yml -f docker-compose.mem0g.yml up -d" -ForegroundColor White
Write-Host "3. Verify services: docker ps" -ForegroundColor White
Write-Host ""
Write-Host "🚀 Ready for COS Phase 2 Sprint 2!" -ForegroundColor Cyan