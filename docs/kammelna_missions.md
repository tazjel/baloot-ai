# Kammelna Intelligence Missions

## Mission: Protocol Decoder 🔓

Build a full binary protocol decoder for Kammelna's custom WebSocket binary format.

### Tasks
- [ ] Analyze the binary header structure (`80 XX XX 12 00 03...`)
- [ ] Map all field type codes (`04`=int32, `08`=string, `05`=float64, `01`=bool, `0c`=array, `12`=struct, `11`=list)
- [ ] Build recursive TLV (Type-Length-Value) parser
- [ ] Create `KammelnaDecoder` class in `tools/kammelna_decoder.py`
- [ ] Decode a full game from `captures/game_capture_v3_autosave_25` into structured JSON
- [ ] Extract complete game timeline: bids → card plays → tricks → scoring

---

## Mission: Game Replay Builder 🎬

Reconstruct full game replays from decoded protocol data.

### Tasks
- [ ] Map card hex IDs (0x00-0x33) to standard card notation (suit+rank)
- [ ] Build turn-by-turn game state reconstruction
- [ ] Compare Kammelna scoring vs our engine's scoring
- [ ] Validate rule differences (if any) between Kammelna and our implementation
- [ ] Export replay as JSON compatible with our frontend's replay format

---

## Mission: Capture Dashboard Integration 📊

Integrate the capture tool into the Baloot AI Dashboard.

### Tasks
- [ ] Add "Kammelna Spy" page to the Dashboard
- [ ] Live WS message counter & protocol decoder viewer
- [ ] One-click capture start/stop from Dashboard
- [ ] Captured game browser with decoded replays
- [ ] Side-by-side comparison: Kammelna game vs our engine's analysis

---

## Mission: Multi-Game Capture 🎯

Capture multiple games to build a training dataset.

### Tasks
- [ ] Auto-save per-game (detect game start/end boundaries)
- [ ] Capture 10+ ranked games at different skill levels
- [ ] Build statistics: average game length, bid distribution, card play patterns
- [ ] Compare human decisions vs our bot's recommendations

---

## Tips & Tricks for Next Session

### Quick Start
```bash
# Run capture tool
python tools/capture_archive.py

# Analyze a capture file
python tools/analyze_capture.py captures/game_capture_v3_autosave_25_20260214_213932.json
```

### Key Files
| File | Purpose |
|---|---|
| `tools/capture_archive.py` | v3.2 capture engine (non-invasive WS interceptor) |
| `tools/analyze_capture.py` | Quick analysis of captured JSON |
| `captures/*.json` | Captured game data (gitignored, keep local) |

### Protocol Cheat Sheet
- **Game WS**: `wss://baloot1.kammelna.com:8443/websocket` — custom binary
- **Social WS**: `wss://kammelna-coordinator-signalr.service.signalr.net` — SignalR JSON
- Binary header: `80 [len_hi] [len_lo]` then TLV-style fields
- Field types: `04`=int32, `08`=string, `05`=float64, `07`=double, `01`=bool, `0c`=int32_array, `12`=struct, `11`=list, `10`=map
- Card encoding: 2-char `{suit}{rank}` where suit=d/h/c/s, rank=a/2-10/j/q/k
- Actions: `a_bid`, `a_card_played`, `a_cards_eating`, `a_accept_next_move`, `a_back`
- Game stages (`gStg`): 0=lobby, 1=bidding, 2=playing, 3=trick-end

### Naming Suggestion
**"Kammelna Spy"** or **"Protocol Spy"** — fits the intelligence/reverse-engineering theme. Could live under Dashboard as a dedicated page alongside Scout and BotLab.

### Architecture Notes
- The binary format is NOT MessagePack, NOT Protobuf — it's a custom TLV format
- Field names are ASCII strings preceded by their length
- Nested structs use `12 00 XX` headers where XX = number of fields
- The `a0` prefix on some messages indicates zlib-compressed payloads
- SignalR social hub uses standard JSON with `\u001e` (Record Separator) delimiter
