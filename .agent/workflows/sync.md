---
description: Sync Kammelna game data from mobile device via ADB wireless
---

# /sync — Daily Kammelna Game Sync

Pulls saved games and highlights from the Kammelna mobile app to a date-organized local folder for analysis and engine benchmarking.

## Prerequisites
- Mobile device must have **Wireless Debugging** enabled (Settings → Developer Options → Wireless debugging)
- Device and PC must be on the **same Wi-Fi network**
- ADB binary: `C:\Users\MiEXCITE\platform-tools\adb.exe`

## Workflow Steps

### 1. Get Pairing Credentials from User
Ask the user for:
- **Pair IP:port** (from "Pair device with pairing code" in Wireless Debugging)
- **Pair code** (6-digit number shown on device)
- **Connect IP:port** (shown at top of Wireless Debugging screen)

### 2. Pair with Device
// turbo
```powershell
C:\Users\MiEXCITE\platform-tools\adb.exe pair <PAIR_IP:PORT> <PAIR_CODE>
```
Expected output: `Successfully paired to <ip>`

### 3. Connect to Device
// turbo
```powershell
C:\Users\MiEXCITE\platform-tools\adb.exe connect <CONNECT_IP:PORT>
```
Expected output: `connected to <ip>`

### 4. Create Today's Sync Folder
// turbo
```powershell
$today = Get-Date -Format "yyyy-MM-dd"
New-Item -ItemType Directory -Force -Path "c:\Users\MiEXCITE\Projects\baloot-ai\gbaloot\data\sync\$today"
```

### 5. Pull Kammelna Game Data
// turbo
```powershell
$today = Get-Date -Format "yyyy-MM-dd"
C:\Users\MiEXCITE\platform-tools\adb.exe -s <CONNECT_IP:PORT> pull /sdcard/Download/kammelna_export/ "c:\Users\MiEXCITE\Projects\baloot-ai\gbaloot\data\sync\$today\kammelna_export"
```
**Source device paths:**
- Saved games: `/sdcard/Download/kammelna_export/savedGames/` (JSON files per game session)
- Highlights: `/sdcard/Download/kammelna_export/highlights/` (notable plays)

**Kammelna app package:** `com.remalit.kammelna`

### 6. Verify Sync
// turbo
```powershell
$today = Get-Date -Format "yyyy-MM-dd"
$saved = (Get-ChildItem "c:\Users\MiEXCITE\Projects\baloot-ai\gbaloot\data\sync\$today\kammelna_export\savedGames" -Filter "*.json").Count
$highlights = (Get-ChildItem "c:\Users\MiEXCITE\Projects\baloot-ai\gbaloot\data\sync\$today\kammelna_export\highlights" -Filter "*.json" -ErrorAction SilentlyContinue).Count
Write-Output "Synced: $saved saved games, $highlights highlights"
```

### 7. Show Recent Games Summary
// turbo
```powershell
$today = Get-Date -Format "yyyy-MM-dd"
$files = Get-ChildItem "c:\Users\MiEXCITE\Projects\baloot-ai\gbaloot\data\sync\$today\kammelna_export\savedGames" -Filter "*.json" | Sort-Object { [long]($_.Name -replace '.*_(\d+)\.json','$1') } -Descending | Select-Object -First 10
foreach ($f in $files) {
  $d = Get-Content $f.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
  $mode = if ($d.gT -eq 1) { "Hokum" } elseif ($d.gT -eq 2) { "Sun" } else { "Mode$($d.gT)" }
  Write-Output "$($d.n) | $mode | Score: $($d.s1)-$($d.s2)"
}
```

## Data Schema Reference

Each saved game JSON has these key fields:
| Key | Description |
|------|-------------|
| `v` | Version |
| `n` | Session name (e.g., "جلسة 1201") |
| `ps` | Player IDs (array of 4) |
| `psN` | Player names (array of 4) |
| `s1` | Team 1 final score |
| `s2` | Team 2 final score |
| `gT` | Game type: 1=Hokum, 2=Sun |
| `t` | Trick count per round (5 for Hokum/Sun standard) |
| `rL` | Round list (detailed round-by-round data) |
| `rs` | Round scores |
| `chA` | Challenge/ashkal actions |
| `pT` | Play type |

## Sync History Directory Structure
```
gbaloot/data/sync/
├── 2026-02-16/
│   └── kammelna_export/
│       ├── savedGames/    (109 JSON files)
│       └── highlights/    (9 JSON files)
├── 2026-02-17/
│   └── ...
```
