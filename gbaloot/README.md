# GBaloot — Baloot Game Data Analysis Tool

A standalone tool for capturing, processing, organizing, reviewing, and acting on Baloot game data.

## Quick Start

```powershell
# From the project root
cd gbaloot
.\launch.ps1

# Or directly
streamlit run gbaloot/app.py --server.port 8502
```

## Sections

| Section | Purpose |
|---------|---------|
| 📡 **Capture** | Launch WebSocket recording sessions, manage capture library |
| ⚙️ **Process** | Decode binary SFS2X captures into structured events |
| 📁 **Organize** | Tag, group, and annotate processed sessions |
| 🔍 **Review** | Deep timeline analysis, action charts, event filtering |
| ✅ **Do** | Task board for analysis action items |

## Architecture

```
gbaloot/
├── app.py              # Main Streamlit entry point
├── launch.ps1          # Desktop launcher
├── core/
│   ├── models.py       # Data models (GameEvent, Session, TaskStore)
│   ├── decoder.py      # SFS2X binary protocol decoder
│   └── capturer.py     # Playwright WebSocket interceptor
├── sections/
│   ├── capture.py      # Capture section UI
│   ├── process.py      # Process section UI
│   ├── organize.py     # Organize section UI
│   ├── review.py       # Review section UI
│   └── do.py           # Do (tasks) section UI
└── data/
    ├── captures/       # Raw capture JSON files
    ├── sessions/       # Processed session files
    └── tasks/          # Task board data
```

## Port

Runs on **port 8502** to avoid conflicts with the main dashboard (8501).
