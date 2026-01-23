Write-Host "=== 🚀 Launching Full Baloot Game Stack (/WW) ===" -ForegroundColor Cyan

# 1. Ensure Docker (and start if needed)
Write-Host "`n[1/4] Checking Infrastructure..." -ForegroundColor Yellow
& ./scripts/ensure_docker.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Wrapper: Docker failed to start. Exiting." -ForegroundColor Red
    exit 1
}

# 2. Redis (Container)
$dockerCheck = docker ps --filter "name=baloot-redis" --format "{{.Names}}"
if ($dockerCheck -match "baloot-redis") {
    Write-Host "✅ Redis is already running." -ForegroundColor Green
} else {
    Write-Host "🚀 Starting Redis container..." -ForegroundColor Yellow
    docker run --name baloot-redis -p 6379:6379 -d redis
}

# 3. Start AI Worker (The Brain)
# Write-Host "`n[2/4] Starting AI Worker..." -ForegroundColor Yellow
# Start-Process powershell -ArgumentList "-NoExit", "-Command", "python ai_worker/worker.py"

# 4. Start Game Server (SocketIO)
Write-Host "`n[3/4] Starting Game Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python run_game_server.py"

# 5. Start Frontend (Vite)
Write-Host "`n[4/4] Starting Frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "`n✅ All services initiated! Check the 3 new windows." -ForegroundColor Green
Write-Host "   Game URL: http://localhost:5173 (usually)" -ForegroundColor Cyan
Write-Host "   Main window will close in 5 seconds..." -ForegroundColor Gray
Start-Sleep -Seconds 5
