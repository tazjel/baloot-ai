$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"

Write-Host "🔍 Checking Docker Status..." -ForegroundColor Cyan

# 1. Check if Process is Running
$process = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if ($process) {
    Write-Host "✅ Docker Desktop process is running." -ForegroundColor Green
} else {
    Write-Host "⚠️  Docker Desktop not running. Attempting to start..." -ForegroundColor Yellow
    if (Test-Path $dockerExe) {
        Start-Process $dockerExe
        Write-Host "🚀 Docker Desktop launched. Waiting for initialization..." -ForegroundColor Cyan
    } else {
        Write-Host "❌ Could not find Docker Desktop at expected path: $dockerExe" -ForegroundColor Red
        exit 1
    }
}

# 2. Wait for Socket / CLI Responsiveness
$maxRetries = 60
$retry = 0
$ready = $false

while ($retry -lt $maxRetries) {
    $retry++
    Write-Host "⏳ Waiting for Docker Daemon ($retry/$maxRetries)..." -NoNewline
    
    try {
        $res = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host " ✅ Ready!" -ForegroundColor Green
            $ready = $true
            break
        }
    } catch {
        # ignore
    }
    Write-Host "."
    Start-Sleep -Seconds 2
}

if ($ready) {
    Write-Host "🎉 Docker is fully operational." -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ Timed out waiting for Docker Daemon." -ForegroundColor Red
    exit 1
}
