param (
    [switch]$UpdateSnapshots
)

# 1. Handle Snapshot Updates
if ($UpdateSnapshots) {
    Write-Host "📸 Resetting snapshots for a fresh baseline..." -ForegroundColor Yellow
    $SnapshotPath = "tests/browser/snapshots"
    if (Test-Path $SnapshotPath) {
        Remove-Item $SnapshotPath -Recurse -Force
        Write-Host "   ✅ Snapshots cleared." -ForegroundColor Gray
    }
}

# 2. Run Tests (Turbo Mode)
Write-Host "🚀 Running Turbo Tests (Headless + Parallel)..." -ForegroundColor Cyan
# Capture exit code but don't stop script -> we want to see the report even on failure
pytest tests/browser/test_ui_qayd.py --video=on --html=diagnostics/report.html --self-contained-html -n auto

# 3. Auto-Open Report
if (Test-Path "diagnostics/report.html") {
    Write-Host "📄 Opening Test Report..." -ForegroundColor Green
    Start-Process "diagnostics/report.html"
} else {
    Write-Host "⚠️ Report not found." -ForegroundColor Red
}
