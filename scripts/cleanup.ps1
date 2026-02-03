Write-Host "🧹 Cleaning up Baloot Game Processes..." -ForegroundColor Cyan

function Kill-By-Command ($pattern) {
    $procs = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match $pattern }
    foreach ($p in $procs) {
        # Avoid killing self or tools
        if ($p.Name -match "python" -and $_.CommandLine -match "cortex") { continue }
        
        Write-Host "   🔪 Killing PID $($p.ProcessId): $($p.CommandLine.Substring(0, [math]::Min(50, $p.CommandLine.Length)))..." -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Kill-Port ($port) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conns) {
        foreach ($c in $conns) {
            $pid_val = $c.OwningProcess
            if ($pid_val -gt 0) {
                 Write-Host "   🔌 Killing PID $pid_val on port $port" -ForegroundColor Yellow
                 Stop-Process -Id $pid_val -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Wait-For-Port-Release ($port) {
    Write-Host "   ⏳ Waiting for port $port to release..." -NoNewline
    for ($i = 0; $i -lt 10; $i++) {
        $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if (-not $conns) {
            Write-Host " Done." -ForegroundColor Green
            return $true
        }
        Start-Sleep -Milliseconds 500
        Write-Host "." -NoNewline
    }
    Write-Host " TIMEOUT!" -ForegroundColor Red
    return $false
}

# 1. Kill by Port (Most Accurate)
Kill-Port 3005 # Backend
Kill-Port 5173 # Frontend

# 2. Kill by Signature (Cleanup orphans)
Kill-By-Command "server.main"
Kill-By-Command "vite"

# 2.5 Kill by Window Title (Close PowerShell Windows)
$targets = @("Baloot Backend", "Baloot Frontend")
foreach ($t in $targets) {
    $wins = Get-Process | Where-Object { $_.MainWindowTitle -eq $t }
    if ($wins) {
        Write-Host "   🪟 Closing Window: $t" -ForegroundColor Yellow
        Stop-Process -InputObject $wins -Force -ErrorAction SilentlyContinue
    }
}

# 3. Redis
$redis = Get-Process redis-server -ErrorAction SilentlyContinue
if ($redis) {
    Write-Host "   🛑 Stopping Local Redis..." -ForegroundColor Yellow
    Stop-Process -Id $redis.Id -Force -ErrorAction SilentlyContinue
}

# 4. Verify Release
Wait-For-Port-Release 3005
Wait-For-Port-Release 5173

Write-Host "✅ Cleanup Complete. Ports 3005, 5173 should be free." -ForegroundColor Green
