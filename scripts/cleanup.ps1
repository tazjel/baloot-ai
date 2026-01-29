Write-Host "🧹 Cleaning up Baloot Game Processes..." -ForegroundColor Cyan

# Kill Python (Backend/AI)
Write-Host "Killing Python..." -ForegroundColor Yellow
taskkill /F /IM python.exe /T 2>$null
taskkill /F /IM pythonw.exe /T 2>$null

# Kill Node (Frontend)
Write-Host "Killing Node..." -ForegroundColor Yellow
taskkill /F /IM node.exe /T 2>$null

# Kill Redis (Optional - usually runs in Docker, but check local)
Write-Host "Killing Local Redis..." -ForegroundColor Yellow
taskkill /F /IM redis-server.exe /T 2>$null
taskkill /F /IM redis-cli.exe /T 2>$null

Write-Host "✅ Cleanup Complete. Ports 3005, 5173, 6379 should be free." -ForegroundColor Green
Write-Host "Ready to run /WW again!" -ForegroundColor Green
