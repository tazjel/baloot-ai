# GBoard Recon Handoff — Live Session Active

> **Time-sensitive**: A live capture session is running RIGHT NOW with Kammelna open in a headed Playwright browser. You have a window to do live JS inspection before we close it.

---

## Current Situation

### Live Capture Session
- **Session**: `recon_live_04` — running for ~30 minutes
- **Status**: Active capture, 2,048+ WS messages collected, 46 screenshots
- **Browser**: Headed Playwright Chromium at `https://kammelna.com/baloot/`
- **Command**: `python gbaloot/capture_session.py --label recon_live_04 --no-pipeline`
- **Data file**: `gbaloot/data/captures/game_capture_recon_live_04_autosave.json`

### What Gemini Already Discovered (via MCP Playwright)

#### Architecture
| Layer | Technology | Version | Role |
|-------|-----------|---------|------|
| Game Engine | Unity WebGL | 3.5.1 | Canvas rendering |
| Networking | **SFS2X** (SmartFoxServer) | 1.7.17 | ALL game traffic — binary over `wss://baloot1.kammelna.com:8443/websocket` |
| Chat | Strophe XMPP | — | ejabberd chat |
| Other | SignalR | 5.0.17 | Non-game services (notifications) |

**Key finding: SignalR is NOT the game protocol.** It's all SFS2X binary.

#### Unity Init Script (extracted from page)
```javascript
createUnityInstance(canvas, config, (progress) => {
    // progress bar update
}).then((unityInstance) => {
    // unityInstance consumed here, NOT stored globally
    loader.style.transform = "scale(0)";
});
```
- Unity instance is **local-scoped** — no `window.unityInstance` available
- No global `SendMessage` access without patching the init script
- `config.productVersion = "3.5.1"`
- Build files: `54f0612.loader.js`, `96407419.data.br`, `57ad27e5.framework.js.br`, `9d29719c.wasm.br`

#### SFS2X Decoder Results
Our existing `SFS2XDecoder` in `gbaloot/core/decoder.py` successfully decoded **16/20 (80%)** of live messages. Failures are:
- `0xA0` frames = zlib-compressed (need to add `zlib.decompress()` before parse)
- `0x3F` frames = keepalive/ping (skip)

#### Decoded Game State Fields (MATCH our specs exactly)
```python
{
    "ss": [6, 0, 6, 1],              # scores per seat
    "gm": "hokom",                    # game mode
    "gStg": 3,                        # stage: 2=playing, 3=trick eating
    "mn": 4,                          # move number
    "pcsCount": [4, 4, 4, 4],        # cards remaining per player
    "played_cards": [38, 36, 32, 45], # card indices on table
    "last_action": {"action": "a_card_played", "ap": 2},
    "dp": [[], ["baloot"], [], []],   # declarations
    "mover": 1,                       # current turn (1-indexed)
    "dealer": 3,                      # dealer seat (1-indexed)
    "switch_seat": {"seat": 4, "dbId": 3820231},
    "pinfo": [                        # player info
        {"n": "Moha -su", "i": 8538487, "pts": 20934, "fsi": "Baloot_Lucky"},
        {"n": "AI 2", "i": -1, "pts": 0},  # Bot player
        {"n": "HAYAYNLK", "i": 3905786, "pts": 31708},
        {"n": "player4", "i": 3820231, "is": true}
    ]
}
```

#### Window Globals Found
- `SFS2X` namespace exists — SFS2X JS API is loaded
- `Strophe` — XMPP client for chat
- `microsoft.signalR` — SignalR 5.0.17 (not for game)
- Standard Unity globals: `unityFramework`, build config

---

## Your Decision Point

### Do you want to run live JS recon before we close the browser?

The Playwright browser is still open at `https://kammelna.com/baloot/`. You can:

1. **Run `page.evaluate()` scripts** to probe deeper into:
   - The SFS2X client instance (`window.SFS2X` namespace) — find the `.send()` method for injecting commands
   - Unity WASM exports — check if `SendMessage` is accessible via the WASM bridge
   - The `unityFramework` object — may hold references to the game instance
   - Any card-play handlers registered as event listeners

2. **Inspect the framework.js** — The decompressed framework (`57ad27e5.framework.js.br`) contains all Unity C# → JS bridge code. We could fetch and search it for `SendMessage`, `PlayCard`, `BidAction` patterns.

3. **Skip live recon** — We have enough data. The WS-level proxy approach (intercept RECV to read state, craft SEND to play) doesn't need Unity access at all.

### How to run live inspection (if you choose to)

The capture session process controls the Playwright browser. To inject JS:

**Option A: Write a one-time recon script**
```python
# gbaloot/recon_inject.py — run alongside the capture session
# Uses a SECOND Playwright instance connecting to the same browser via CDP
```

**Option B: Modify capture_session.py temporarily**
Add a `--recon` flag that pauses after page load and runs your JS probes.

**Option C: Use the captured data only**
The autosave JSON has 2,048 WS messages. Process them offline with the decoder.

---

## Key Files to Read

| File | Why |
|------|-----|
| `gbaloot/core/decoder.py` | SFS2X binary decoder — works on live data |
| `gbaloot/core/reconstructor.py` | Builds game state from decoded events |
| `gbaloot/core/card_mapping.py` | Source card index ↔ Card object |
| `gbaloot/core/state_builder.py` | (TO BUILD) SFS2X events → BotAgent game_state |
| `gbaloot/core/gboard.py` | (TO BUILD) JS injection actuator |
| `gbaloot/docs/claude_autopilot_instructions.md` | Full spec for StateBuilder + GBoard |
| `gbaloot/data/captures/game_capture_recon_live_04_autosave.json` | 2,048 captured WS messages |

---

## Next Steps (After You Decide on Live Recon)

1. **Add 0xA0 support** to `SFS2XDecoder` — zlib decompress before parsing
2. **Build `StateBuilder`** — translate decoded events → `game_state` dict for BotAgent
3. **Build `GBoard`** — either JS injection (if we find SendMessage) or WS-level command crafting
4. **Build `AutopilotSession`** — main loop: capture → decode → state → bot → execute
