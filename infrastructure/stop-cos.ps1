# COS Infrastructure Shutdown Script
# KISS approach: Clean shutdown with verification

Write-Host "🛑 Stopping COS Infrastructure..." -ForegroundColor Red

# Navigate to infrastructure directory
Set-Location "G:\cos\infrastructure"

# Stop all services cleanly (unified approach)
Write-Host "🔄 Stopping all COS services..." -ForegroundColor Yellow
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml -f docker-compose.mem0g.yml down --remove-orphans

# Verify complete shutdown
Write-Host "`n📊 Verification:" -ForegroundColor Cyan
$remaining = docker ps --format "table {{.Names}}\t{{.Status}}" | Where-Object { $_ -match "cos_" }
if ($remaining) {
    Write-Host "⚠️  Some containers still running:" -ForegroundColor Yellow
    $remaining | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
} else {
    Write-Host "✅ All COS services stopped cleanly" -ForegroundColor Green
}

# Data preservation summary
Write-Host "`n💾 Data Preservation Status:" -ForegroundColor Cyan
@("P:\postgres_cos_dev", "E:\redis_cos_data", "F:\neo4j_cos_data", "F:\elasticsearch_cos_data") | ForEach-Object {
    if (Test-Path $_) {
        $size = (Get-ChildItem $_ -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB
        Write-Host "✅ $_ - $([math]::Round($size, 2)) MB preserved" -ForegroundColor Green
    } else {
        Write-Host "❌ $_ - Missing!" -ForegroundColor Red
    }
}

Write-Host "`n🎯 COS Infrastructure shutdown complete!" -ForegroundColor Green
Write-Host "Ready to restart with: .\start-cos.ps1" -ForegroundColor Gray
