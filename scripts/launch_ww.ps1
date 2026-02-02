Write-Host "=== 🚀 Launching Full Baloot Game Stack (/WW) ===" -ForegroundColor Cyan

# 1. Cleanup First
Write-Host "invoking cleanup..." -ForegroundColor Gray
& ./scripts/cleanup.ps1

# 2. Redis Strategy (Local -> Docker)
$redis_running = Get-Process redis-server -ErrorAction SilentlyContinue

if ($redis_running) {
    Write-Host "✅ Local Redis is running (PID: $($redis_running.Id))." -ForegroundColor Green
} else {
    Write-Host "⚠️ Local Redis not running. Checking for Docker..." -ForegroundColor Yellow
    
    # 1. Ensure Docker is running (Only if we need it)
    & ./scripts/ensure_docker.ps1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Wrapper: Docker failed to start AND Local Redis is missing." -ForegroundColor Red
        # Fallthrough to error message below...
    }
    
    # Check Docker
    $docker_running = docker ps --filter "name=baloot-redis" --format "{{.Names}}"
    $docker_exists = docker ps -a --filter "name=baloot-redis" --format "{{.Names}}"
    
    if ($docker_running -match "baloot-redis") {
        Write-Host "✅ Redis Container is running." -ForegroundColor Green
    } elseif ($docker_exists -match "baloot-redis") {
        Write-Host "🔄 Starting existing Redis Container..." -ForegroundColor Yellow
        docker start baloot-redis
    } else {
        # Try to run container if docker is available
        if (Get-Command docker -ErrorAction SilentlyContinue) {
             Write-Host "🚀 Creating and Starting Redis Container..." -ForegroundColor Yellow
             docker run --name baloot-redis -p 6379:6379 -d redis
        } else {
             Write-Host "❌ Redis not found (Local or Docker). Please install Redis or Docker." -ForegroundColor Red
             # We don't exit here, might be running elsewhere? But huge risk.
             Write-Host "   Continuing, but Game State persistence will fail." -ForegroundColor Red
        }
    }
}

# 3. Start Game Server (SocketIO)
Write-Host "`n[3/4] Starting Game Server..." -ForegroundColor Yellow
# Clear Log
"" | Out-File "logs/server_debug.log" -Encoding utf8
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m server.main"

# 4. Start Frontend (Vite)
Write-Host "`n[4/4] Starting Frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "`n✅ All services initiated! Check the 2 new windows." -ForegroundColor Green
Write-Host "   Game URL: http://localhost:5173" -ForegroundColor Cyan
Write-Host "   Main window will close in 5 seconds..." -ForegroundColor Gray
Start-Sleep -Seconds 5
