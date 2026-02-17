---
description: Sync Baloot game data from mobile device via ADB wireless
---

# /sync — Mobile Game Data Sync

// turbo-all

Pulls saved games and highlights from the mobile app to a date-organized local folder for engine benchmarking.

## Prerequisites
- **Wireless Debugging** enabled on device (Settings → Developer Options → Wireless debugging)
- Device and PC on **same Wi-Fi network**

## Device Config (saved — rarely changes)
```powershell
$ADB = "C:\Users\MiEXCITE\platform-tools\adb.exe"
$DEVICE_IP = "192.168.100.10"
$TODAY = Get-Date -Format "yyyy-MM-dd"
$SYNC_DIR = "c:\Users\MiEXCITE\Projects\baloot-ai\gbaloot\data\sync\$TODAY\mobile_export"
$DEVICE_PATH = "/sdcard/Download/kammelna_export/"
```

> **Note**: `$DEVICE_IP` is saved from the last successful connection. Update if the user's Wi-Fi IP changes.
> **Note**: `$DEVICE_PATH` is the real path on the device — it cannot be renamed.

## Step 1: Auto-Reconnect (try first — no user input needed)

Try to reconnect using a previously paired device. ADB remembers paired devices.

```powershell
$connected = (& $ADB devices | Select-String "$DEVICE_IP" | Measure-Object).Count
if ($connected -gt 0) {
    Write-Output "Already connected to $DEVICE_IP"
} else {
    Write-Output "Not connected. Attempting reconnect..."
    # Try common ports (ADB wireless debugging typically uses 5555 or recently seen ports)
    $ports = @(35363, 5555, 40891, 37000, 38000, 39000, 40000, 41000, 42000, 43000, 44000, 45000)
    $found = $false
    foreach ($port in $ports) {
        $result = & $ADB connect "${DEVICE_IP}:${port}" 2>&1
        if ($result -match "connected to") {
            Write-Output "Auto-connected on port $port"
            $found = $true
            $env:ADB_DEVICE = "${DEVICE_IP}:${port}"
            break
        }
    }
    if (-not $found) {
        Write-Warning "Auto-reconnect failed. Need manual pairing (Step 2)."
    }
}
```

If auto-reconnect succeeds → **skip to Step 3**.
If it fails → proceed to Step 2 (manual pairing).

## Step 2: Manual Pair (only if auto-reconnect failed)

Ask the user for:
- **Connect IP:port** — shown at top of Wireless Debugging screen
- **Pair code** — 6-digit, from "Pair device with pairing code"
- **Pair IP:port** — shown next to the pairing code

```powershell
& $ADB pair <PAIR_IP:PORT> <PAIR_CODE>
& $ADB connect <CONNECT_IP:PORT>
```
Expected: `Successfully paired` then `connected to <ip>`

> After pairing, update the `$ports` array in Step 1 with the new connect port for future auto-reconnect.

## Step 3: Pull Game Data

```powershell
New-Item -ItemType Directory -Force -Path $SYNC_DIR | Out-Null
& $ADB pull $DEVICE_PATH $SYNC_DIR
```

**Device source paths:**
- `savedGames/` — JSON per game session
- `highlights/` — notable plays

**App package:** `com.remalit.kammelna`

## Step 4: Verify & Summarize

```powershell
# ADB pull nests the source folder name, so check both possible paths
$base = if (Test-Path "$SYNC_DIR\savedGames") { $SYNC_DIR } else { "$SYNC_DIR\kammelna_export" }
$saved = (Get-ChildItem "$base\savedGames" -Filter "*.json" -ErrorAction SilentlyContinue).Count
$highlights = (Get-ChildItem "$base\highlights" -Recurse -Filter "*.json" -ErrorAction SilentlyContinue).Count
Write-Output "Synced: $saved saved games, $highlights highlights"

if ($saved -eq 0) { Write-Warning "No games found — check device path or ADB connection" }
```

## Step 5: Show Recent Games

```powershell
$files = Get-ChildItem "$base\savedGames" -Filter "*.json" -ErrorAction SilentlyContinue |
  Sort-Object { [long]($_.Name -replace '.*_(\d+)\.json','$1') } -Descending |
  Select-Object -First 10
foreach ($f in $files) {
  $d = Get-Content $f.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
  $mode = if ($d.gT -eq 1) { "Hokum" } elseif ($d.gT -eq 2) { "Sun" } else { "Mode$($d.gT)" }
  Write-Output "$($d.n) | $mode | Score: $($d.s1)-$($d.s2)"
}
```

## Step 6: Clean Device (optional — ask user first)

```powershell
& $ADB shell rm -rf $DEVICE_PATH
Write-Output "Device data cleared."
```

## Data Schema Quick Ref

| Key | Description |
|-----|-------------|
| `n` | Session name (e.g., "جلسة 1201") |
| `gT` | Game type: 1=Hokum, 2=Sun |
| `s1`/`s2` | Team scores |
| `ps`/`psN` | Player IDs / names (array of 4) |
| `rL` | Round list (detailed round data) |
| `chA` | Challenge/ashkal actions |

## Directory Structure
```
gbaloot/data/sync/
├── 2026-02-16/
│   └── mobile_export/
│       └── kammelna_export/
│           ├── savedGames/    (JSON files)
│           └── highlights/    (JSON files)
└── 2026-02-17/
    └── ...
```
