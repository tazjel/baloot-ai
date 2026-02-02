$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== 🔄 Restarting Baloot Game Environment ===" -ForegroundColor Cyan

# 1. Cleanup
& ./scripts/cleanup.ps1

# 2. Launch Backend
Write-Host "`n[2/3] Launching Backend..."
$logFile = "logs/server_debug.log"
$logFileErr = "logs/server_error.log"
# Clear log files
"" | Out-File $logFile -Encoding utf8
"" | Out-File $logFileErr -Encoding utf8

$pythonPath = (Get-Command "python" -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    Write-Host "❌ Python not found in PATH!" -ForegroundColor Red
    exit 1
}
Write-Host "   ℹ️  Using Python: $pythonPath" -ForegroundColor Gray

try {
    # Using -u for unbuffered output
    $serverProcess = Start-Process $pythonPath -ArgumentList "-u", "-m", "server.main" -RedirectStandardOutput $logFile -RedirectStandardError $logFileErr -PassThru -ErrorAction Stop
    Write-Host "   ✅ Backend started (PID: $($serverProcess.Id))." -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to launch backend process! Error: $_" -ForegroundColor Red
    exit 1
}

# 3. Launch Frontend
Write-Host "`n[3/3] Launching Frontend..."
Set-Location "frontend"
# Run hidden or minimized? User usually wants to see errors. Hidden is good for restarts if main window persists.
# But here we are restarting everything.
$frontendProcess = Start-Process powershell -ArgumentList "-Command", "npm run dev" -PassThru -WindowStyle Minim
Set-Location ..
Write-Host "   ✅ Frontend started (PID: $($frontendProcess.Id))." -ForegroundColor Green

Write-Host "`n🎉 Restart Complete! Game ready at http://localhost:5173" -ForegroundColor Cyan
