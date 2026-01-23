
Write-Host "--- Automated Scout Routine ---" -ForegroundColor Cyan

$LogFile = "logs/server_manual.log"

# 1. Archive old logs (Optional cleanup)
if (Test-Path $LogFile) {
    $Size = (Get-Item $LogFile).Length
    if ($Size -gt 5MB) {
        Write-Host "Log file too large ($Size bytes). Rotating..."
        Move-Item $LogFile "logs/server_manual_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    }
}

# 2. Run Game Verification (Simulation) to generate logs
Write-Host "Starting Game Simulation to generate data..."
$SimProcess = Start-Process python -ArgumentList "scripts/verify_game_flow.py", "--duration", "300" -PassThru -NoNewWindow
$SimProcess | Wait-Process

Write-Host "Simulation Complete." -ForegroundColor Green

# 3. Run The Scout
Write-Host "Releasing The Scout..." -ForegroundColor Yellow
python scripts/scout.py

Write-Host "Scout Routine Finished." -ForegroundColor Cyan
