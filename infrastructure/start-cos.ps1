# COS Infrastructure Unified Startup Script
# KISS approach: One command, zero orphans, all services healthy

Write-Host "🧠 Starting COS Infrastructure..." -ForegroundColor Cyan

# Navigate to infrastructure directory
Set-Location "G:\cos\infrastructure"

# Clean shutdown first (prevents any conflicts)
Write-Host "🔄 Ensuring clean state..." -ForegroundColor Yellow
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml -f docker-compose.mem0g.yml down --remove-orphans 2>$null

# Start ALL services together (eliminates orphan warnings)
Write-Host "🚀 Starting all COS services..." -ForegroundColor Green
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml -f docker-compose.mem0g.yml up -d

# Wait for services to initialize
Write-Host "⏳ Waiting for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 36

# Comprehensive health verification
Write-Host "🏥 Service Status:" -ForegroundColor Cyan
$containers = docker ps --format "table {{.Names}}\t{{.Status}}" | Where-Object { $_ -match "cos_" }
$containers | ForEach-Object {
    if ($_ -match "healthy") {
        Write-Host "✅ $_" -ForegroundColor Green
    } elseif ($_ -match "Up") {
        Write-Host "⚠️  $_" -ForegroundColor Yellow
    } else {
        Write-Host "❌ $_" -ForegroundColor Red
    }
}

# Quick connectivity tests
Write-Host "`n🌐 Connectivity:" -ForegroundColor Cyan
try {
    $traefik = Invoke-WebRequest -Uri "http://localhost:8080" -UseBasicParsing -TimeoutSec 3
    Write-Host "✅ Traefik Dashboard ($($traefik.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Traefik unreachable" -ForegroundColor Red
}

try {
    $neo4j = Invoke-WebRequest -Uri "http://localhost:7474" -UseBasicParsing -TimeoutSec 3
    Write-Host "✅ Neo4j Browser ($($neo4j.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Neo4j unreachable" -ForegroundColor Red
}

try {
    $redis = docker exec -e REDISCLI_AUTH="Police9119!!Red" cos_redis redis-cli ping 2>$null
    if ($redis -eq "PONG") {
        Write-Host "✅ Redis Authentication" -ForegroundColor Green
    } else {
        Write-Host "❌ Redis Authentication failed" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Redis unreachable" -ForegroundColor Red
}

# Service access points
Write-Host "`n📋 Access Points:" -ForegroundColor White
Write-Host "📊 Traefik Dashboard: http://localhost:8080" -ForegroundColor Gray
Write-Host "🧬 Neo4j Browser: http://localhost:7474" -ForegroundColor Gray
Write-Host "🗄️  PostgreSQL Dev: localhost:5433" -ForegroundColor Gray
Write-Host "🔴 Redis: docker exec -e REDISCLI_AUTH=\"Police9119!!Red\" cos_redis redis-cli [command]" -ForegroundColor Gray

Write-Host "`n🎯 COS Infrastructure Ready for Phase B Development!" -ForegroundColor Magenta
