
Write-Host "Rebooting Game Server Stack..." -ForegroundColor Cyan

# 1. Kill Python Processes (Aggressive)
Write-Host "Killing Python processes..."
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*run_game_server*" -or $_.CommandLine -like "*run_game_server.py*" -or $_.CommandLine -like "*worker.py*" } | Stop-Process -Force

# Kill explicit PIDs if any linger
$ports = @(3005, 8080)
foreach ($port in $ports) {
    $p = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($p) {
        Write-Host "Killing process on port $port..."
        Stop-Process -Id $p.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

# 2. Start AI Worker
Write-Host "Starting AI Worker..."
Start-Process -FilePath "python" -ArgumentList "ai_worker/worker.py" -WindowStyle Minimized

# 3. Start Game Server
Write-Host "Starting Game Server..."
Start-Process -FilePath "python" -ArgumentList "run_game_server.py" -NoNewWindow

Write-Host "Server Stack Restarted." -ForegroundColor Green
