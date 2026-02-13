---
description: Run pytest via the Dashboard Test Manager (browser). All pytest work MUST go through the Dashboard.
---

# Agent Rule: All Pytest → Dashboard

> **MANDATORY**: Never run `python -m pytest` directly in the terminal. Always use the Dashboard's 🧪 Test Manager tab via Playwright.
> **MANDATORY**: Always use Playwright MCP tools (`mcp_playwright_*`) to interact with the Dashboard. NEVER use `browser_subagent` — it is too slow.
> **MANDATORY**: Always ensure Docker Desktop is running before launching the Dashboard. Redis depends on Docker.

## Step 0: Ensure Docker Desktop is Running

Check if Docker Desktop is running. If not, launch it and wait.

// turbo
```powershell
$docker = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $docker) { Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"; Start-Sleep 5; Write-Host "Docker Desktop launched" } else { Write-Host "Docker Desktop already running" }
```

## Step 1: Ensure Dashboard is Running

Check if the Dashboard is already running on port 8501. If not, launch it:

// turbo
```powershell
$running = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue
if (-not $running) { Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File ./tools/dashboard/launch.ps1' -WindowStyle Minimized; Start-Sleep 4; Write-Host 'Dashboard launched' } else { Write-Host 'Dashboard already running' }
```

## Step 2: Navigate to Dashboard (Playwright)

Use `mcp_playwright_browser_navigate` to open `http://localhost:8501`.
Then use `mcp_playwright_browser_snapshot` to verify the page loaded.

## Step 3: Click the 🧪 Test Manager Tab (Playwright)

Use `mcp_playwright_browser_snapshot` to find the Test Manager tab element.
Click it with `mcp_playwright_browser_click`.
Wait for "Run Controls" text to appear with `mcp_playwright_browser_wait_for`.

## Step 4: Configure Test Scope (Playwright)

- **All tests**: Leave scope dropdown as "All Tests" (default)
- **Specific module**: Use `mcp_playwright_browser_click` on the scope dropdown, then select the target module

## Step 5: Set Options (Playwright)

Check/uncheck as needed via `mcp_playwright_browser_click`:
- ☐ Verbose (-v)
- ☐ Stop on fail (-x)  
- ☐ Rerun failed (--lf)
- ☐ ⚡ Parallel
- ☑ 📊 Coverage (ON by default)

## Step 6: Run Tests (Playwright)

Click the **▶️ Run Tests** button with `mcp_playwright_browser_click`.
Wait for results — use `mcp_playwright_browser_wait_for` with sufficient timeout (tests can take up to 30s).
Then `mcp_playwright_browser_snapshot` to read the results banner.

## Step 7: Read Results (Playwright)

- **✅ All passed**: Take a snapshot, report to user, continue coding.
- **❌ Failures**: Click the "❌ Failures" sub-tab, snapshot the error details, fix code, re-run from Step 6.

## Important Notes

- Test history: `tools/dashboard/test_history.json`
- JSON reports: `tools/dashboard/test_report.json`  
- Coverage reports: `tools/dashboard/coverage.json`
- If Dashboard is unreachable, report to user — do NOT fallback to terminal pytest
