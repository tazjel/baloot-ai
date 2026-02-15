# GBaloot Capture System — Claude Review Brief

## Context

GBaloot is a capture-and-benchmark tool that records live Baloot game data from professional platforms via WebSocket interception, then runs the captured data through our engine to verify correctness.

### Pipeline
```
Capture → Decode (SFS2X binary) → Extract Tricks → Compare (dual-engine) → Benchmark Scorecard
```

### New System Built Today

We built 5 improvements to the capture workflow:

| # | Improvement | File | Status |
|---|-------------|------|--------|
| 1 | Event-triggered screenshots | `capturer.py` (classify_event) | ✅ |
| 2 | Session labeling convention | `capture_session.py` (--label) | ✅ |
| 3 | Single-command CLI launcher | `capture_session.py` | ✅ |
| 4 | Post-session auto-pipeline | `capture_session.py` (run_post_pipeline) | ✅ |
| 5 | Screenshot diff utility | `tools/screenshot_diff.py` | ✅ |

---

## Files to Review

### Core Capture
- **`gbaloot/capture_session.py`** — CLI entry point (~295 lines). Launches Playwright, injects WS interceptor, collects messages, takes screenshots, autosaves, and runs post-pipeline on exit.
- **`gbaloot/core/capturer.py`** — WS interceptor JS + GameCapturer class + new event classification helpers (`classify_event`, `classify_batch`, `GAME_EVENT_KEYWORDS`).

### Analysis Tools  
- **`gbaloot/tools/screenshot_diff.py`** — Compares sequential screenshots using SSIM or pixel diff to detect board state transitions.

### Existing Pipeline (for context)
- `gbaloot/core/decoder.py` — SFS2X binary decoder
- `gbaloot/core/trick_extractor.py` — Extracts tricks from decoded events
- `gbaloot/core/comparator.py` — Compares tricks against our engine
- `gbaloot/sections/benchmark.py` — Generates scorecard and confidence badges

---

## Review Questions

Please analyze the following and present your ideas:

### 1. Architecture & Code Quality
- Is the separation between `capture_session.py` (CLI orchestrator) and `capturer.py` (low-level WS capture) clean?
- Are there edge cases in the event classification that could cause missed events or false positives?
- Is the post-pipeline integration clean, or should it be a separate step?

### 2. Event Detection Improvements
- The current `GAME_EVENT_KEYWORDS` dict uses simple string matching on WS message data.
- Could we improve detection accuracy? Should we decode the SFS2X binary first and then match on structured fields?
- What game events are we potentially missing?

### 3. Screenshot Strategy
- We take screenshots on: initial load, periodic interval, game events (bid, card played, trick won, round over), and final save.
- Should we add adaptive screenshot intervals (more frequent during active play, less during waiting)?
- What about screenshot annotation — overlaying metadata (trick number, scores) on the images?

### 4. Benchmark Pipeline Enhancements
- The auto-pipeline runs decode → extract → compare on session end.
- Should we add real-time comparison during capture (compare each trick as it happens)?
- How could we make the divergence reports more actionable?

### 5. Data Organization & Storage
- Sessions are labeled like `hokum_aggressive_01`, screenshots go in `screenshots/{label}/`.
- Should we add a session manifest (JSON index of all sessions with metadata)?
- What about data retention policies for old captures?

### 6. Robustness & Error Handling
- Browser disconnections during long capture sessions.
- What if the game platform changes their WebSocket protocol or obfuscates traffic?
- How to handle partial captures (game interrupted mid-round)?

### 7. Advanced Features (Future)
- Live dashboard showing capture stats in a separate browser tab.
- AI-powered screenshot analysis (what's happening on the board).
- Multiplayer observer mode (capture from spectator perspective).
- Automated game replay from captured data.

---

## How to Provide Feedback

Structure your response as:

```
## Review Summary
(One paragraph: overall assessment)

## Specific Recommendations  
### [Category from above]
- Recommendation: ...
- Priority: High/Medium/Low
- Effort: Small/Medium/Large

## Code Suggestions
(Actual code changes or patterns you'd recommend)

## Strategic Ideas
(Longer-term vision for the capture system)
```
