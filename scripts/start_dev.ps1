Write-Host "=== 🚀 Starting Baloot Dev Environment ===" -ForegroundColor Cyan

# 1. Check Redis
$redisRunning = $false
try {
    $dockerCheck = docker ps --filter "name=redis" --format "{{.Names}}"
    if ($dockerCheck -match "redis") {
        Write-Host "✅ Redis is running (Docker)." -ForegroundColor Green
        $redisRunning = $true
    }
} catch {
    Write-Host "⚠️  Docker not found or error checking." -ForegroundColor Yellow
}

if (-not $redisRunning) {
    Write-Host "⚠️  Redis not detected. Attempting to start default container..." -ForegroundColor Yellow
    try {
        docker-compose up -d redis
    } catch {
        Write-Host "❌ Failed to start Redis. Game will run in fallback mode." -ForegroundColor Red
    }
}

# 2. Start Backend
Write-Host "`n--> Starting Backend Server (New Window)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m server.main"

# 3. Start Frontend
Write-Host "`n--> Starting Frontend (New Window)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm start"

Write-Host "`n✅ Environment Launching! Check the new windows." -ForegroundColor Green
Write-Host "   Backend: http://localhost:8000 (approx)"
Write-Host "   Frontend: http://localhost:3000"
