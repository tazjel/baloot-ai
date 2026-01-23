$ErrorActionPreference = "SilentlyContinue"

Write-Host "Stopping existing Game Server (Port 3005) and Frontend (Port 5173)..."

function Kill-Port ($port) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conns) {
        foreach ($conn in $conns) {
            $pid_val = $conn.OwningProcess
            if ($pid_val -gt 0) {
               Write-Host "Killing Process ID $pid_val on port $port"
               Stop-Process -Id $pid_val -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

Kill-Port 3005
Kill-Port 5173

# Fallback clean up by name just in case
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2

Write-Host "Starting Game Server..."
$serverProcess = Start-Process powershell -ArgumentList "-Command", "python run_game_server.py" -PassThru -WindowStyle Hidden

Write-Host "Starting Frontend (Vite)..."
Set-Location "frontend"
$frontendProcess = Start-Process powershell -ArgumentList "-Command", "npm run dev" -PassThru -WindowStyle Hidden
Set-Location ..

Write-Host "Clean restart initiated. Processes are running in the background."
