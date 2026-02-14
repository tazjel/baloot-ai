<# ──────────────────────────────────────────────
#  GBaloot Launcher
#  Double-click or run from PowerShell to start
# ──────────────────────────────────────────────
$ErrorActionPreference = "Stop"

$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
$GBALOOT_DIR  = Join-Path $PROJECT_ROOT "gbaloot"
$APP_FILE     = Join-Path $GBALOOT_DIR "app.py"

Write-Host ""
Write-Host "  🎮 GBaloot — Baloot Game Data Analysis" -ForegroundColor Cyan
Write-Host "  ────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

# Check streamlit is installed
$streamlit = Get-Command streamlit -ErrorAction SilentlyContinue
if (-not $streamlit) {
    Write-Host "  ❌ Streamlit not found. Install with: pip install streamlit" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check app file exists
if (-not (Test-Path $APP_FILE)) {
    Write-Host "  ❌ App file not found at: $APP_FILE" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "  ▶ Starting on http://localhost:8502" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop" -ForegroundColor DarkGray
Write-Host ""

Set-Location $PROJECT_ROOT
streamlit run $APP_FILE --server.port 8502 --server.headless true --theme.base dark
