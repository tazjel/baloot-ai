---
description: Run the True "Human-Like" Browser Verification for Qayd. Uses Playwright to click buttons and capture snapshots.
---

1. Launch the Browser Verification Script
   > This script launches a headless browser, interacts with the UI, and saves snapshots to `diagnostics/`.
// turbo
pytest tests/browser/test_ui_qayd.py --video=on --reruns 2 --html=diagnostics/report.html --self-contained-html --tracing=retain-on-failure -n auto
