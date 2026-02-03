param (
    [switch]$Headless
)

Write-Host "=== 🚀 Launching Full Baloot Game Stack (/WW) ===" -ForegroundColor Cyan
if ($Headless) { Write-Host "   👻 HEADLESS MODE ACTIVE" -ForegroundColor DarkGray }

# 1. Cleanup First
Write-Host "invoking cleanup..." -ForegroundColor Gray
& ./scripts/cleanup.ps1

function Wait-For-Http ($port, $name) {
    Write-Host "   ⏳ Waiting for $name (Port $port)..." -NoNewline
    $url = "http://127.0.0.1:$port"
    if ($name -eq "Backend") { $url += "/health" }
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -Method Get -TimeoutSec 1 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host " ✅ UP" -ForegroundColor Green
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 1000
            Write-Host "." -NoNewline
        }
    }
    Write-Host " ❌ TIMEOUT" -ForegroundColor Red
    return $false
}

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
if ($Headless) {
    $serverLogOut = "logs/server_headless.out.log"
    $serverLogErr = "logs/server_headless.err.log"
    Write-Host "   Log -> $serverLogOut" -ForegroundColor Gray
    Stop-Process -Name "python" -ErrorAction SilentlyContinue # Double check cleanup
    Start-Process python -ArgumentList "-m", "server.main" -WindowStyle Hidden -RedirectStandardOutput $serverLogOut -RedirectStandardError $serverLogErr
} else {
    # Clear Log
    "" | Out-File "logs/server_debug.log" -Encoding utf8
    $cmd = '$host.ui.RawUI.WindowTitle = ''Baloot Backend''; python -m server.main'
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd
}

# 4. Start Frontend (Vite)
Write-Host "`n[4/4] Starting Frontend..." -ForegroundColor Yellow
if ($Headless) {
    $frontendLogOut = "logs/frontend_headless.out.log"
    $frontendLogErr = "logs/frontend_headless.err.log"
    Write-Host "   Log -> $frontendLogOut" -ForegroundColor Gray
    Start-Process cmd -ArgumentList "/c", "cd frontend && npm run dev" -WindowStyle Hidden -RedirectStandardOutput $frontendLogOut -RedirectStandardError $frontendLogErr
} else {
    $cmd = '$host.ui.RawUI.WindowTitle = ''Baloot Frontend''; cd frontend; npm run dev'
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd
}

Write-Host "`n✅ All services initiated!" -ForegroundColor Green

# 5. Robust Health Check (Agent Verification)
if ($Headless) {
    Write-Host "`n🔍 Verifying Service Health..." -ForegroundColor Cyan
    $be = Wait-For-Http 3005 "Backend"
    $fe = Wait-For-Http 5173 "Frontend"
    
    if (-not ($be -and $fe)) {
        Write-Host "❌ Health Check Failed. Dumping last logs:" -ForegroundColor Red
        Get-Content "logs/server_headless.err.log" -Tail 20
        Write-Error "Deployment failed."
    }
    
    Write-Host "   Use 'Get-Content logs/server_headless.out.log -Tail 10' to monitor." -ForegroundColor Cyan
} else {
    Write-Host "   Check the 2 new windows." -ForegroundColor Cyan
    Write-Host "   Main window will close in 5 seconds..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
}
