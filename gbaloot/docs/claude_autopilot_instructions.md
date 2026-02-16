# Mission: Build the GBaloot Autopilot

**Objective**: Build a closed-loop autopilot that lets our `BotAgent` play autonomously
on the Source platform (source platform) by intercepting SFS2X WebSocket traffic, translating
it into the `game_state` dict BotAgent expects, obtaining decisions, and **injecting
JavaScript directly into the game framework** to execute moves — no pixel clicking.

> **Context**: The Source platform uses **SmartFoxServer 2X (SFS2X)** as its
> multiplayer backend. All game logic is communicated via binary WebSocket frames.
> We already have a full decoder (`gbaloot/core/decoder.py`) and a game reconstructor
> (`gbaloot/core/reconstructor.py`). This mission bridges the gap from passive
> capture to active play.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         source platform (Browser Tab)                               │
│  ┌──────────┐   WS Binary    ┌──────────┐   GameEvent[]   ┌─────────────┐  │
│  │  SFS2X   │───────────────▶│ Decoder  │────────────────▶│ StateBuilder│  │
│  │  Server  │                │(existing)│                 │   (NEW)     │  │
│  └──────────┘                └──────────┘                 └──────┬──────┘  │
│       ▲                                                          │          │
│       │  JS Injection                              game_state dict          │
│  ┌────┴─────┐        Decision dict          ┌───────┴──────────┐           │
│  │  GBoard  │◀──────────────────────────────│    BotAgent      │           │
│  │  (NEW)   │ page.evaluate() → game API    │   (existing)     │           │
│  └──────────┘                               └──────────────────┘           │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Status | File | Role |
|-----------|--------|------|------|
| `GameCapturer` | Existing | `gbaloot/core/capturer.py` | Playwright WS interceptor, saves raw binary frames |
| `SFS2XDecoder` | Existing | `gbaloot/core/decoder.py` | Decodes SFS2X binary → `GameEvent` dicts |
| `GameReconstructor` | Existing | `gbaloot/core/reconstructor.py` | Builds `BoardState` from events (for Review tab) |
| `card_mapping` | Existing | `gbaloot/core/card_mapping.py` | Bidirectional Source index ↔ Card conversion |
| `StateBuilder` | **NEW** | `gbaloot/core/state_builder.py` | Translates SFS2X events → BotAgent `game_state` dict |
| `GBoard` | **NEW** | `gbaloot/core/gboard.py` | **JS Injection actuator** — reverse-engineers game API, calls handlers directly |
| `AutopilotSession` | **NEW** | `gbaloot/autopilot.py` | Main loop orchestrator |



---

## Part 1: The SFS2X Protocol — What You MUST Know

### 1.1 Binary Frame Format

Source uses SFS2X binary protocol over WebSocket. Key details from `decoder.py`:

```python
# Frame headers (first byte)
0x80 = Standard SFSObject message
0xA0 = zlib-compressed message (decompress, then parse as 0x80)

# Type codes (core)
TYPE_NULL       = 0x00    TYPE_BOOL       = 0x01
TYPE_SHORT      = 0x03    TYPE_INT        = 0x04
TYPE_DOUBLE     = 0x06    TYPE_UTF_STRING = 0x08
TYPE_SFS_OBJECT = 0x12    TYPE_SFS_ARRAY  = 0x13
TYPE_INT_ARRAY  = 0x0E    TYPE_SHORT_ARRAY= 0x0D
```

The decoder's `SFS2XDecoder.decode_message(data: bytes)` returns a dict with:
- `"a"` → action code (int, e.g. 1=ExtensionResponse, 4=JoinRoom)
- `"p"` → parameters as nested SFSObject containing `"p"` → the actual game payload

### 1.2 The Critical Payload Path

ALL game events arrive via **ExtensionResponse** (`a=1`). The game payload is at:

```python
decoded["p"]["p"]  # The nested "p" → "p" structure
```

This inner payload contains game-specific fields. The `cmd` field identifies the event.

### 1.3 SFS2X Event Classification (from `event_types.py`)

Our decoder classifies events into these categories:

| Category | Events | Keywords |
|----------|--------|----------|
| `bid_phase` | Bidding actions | `bidAction`, `endBid`, `a_start_bid` |
| `card_played` | Card plays | `a_play`, `playCard`, `cardPlayed` |
| `trick_won` | Trick eating | `a_cards_eating`, `trickWon`, `eatCards` |
| `round_over` | Round/game end | `endGame`, `gameResult`, `roundOver` |
| `game_state` | State snapshots | `game_state`, `a_game_state_change` |
| `connection` | Connect/disconnect | `ws_connect`, `ws_disconnect`, `onLogin` |
| `player` | Player join/leave | `onUserEnter`, `onUserLeave`, `onSpectator` |
| `sfs_cmd` | SFS2X internal | `deal`, `lobbyJoin`, `init` |
| `chat` | Chat messages | `chat`, `publicMessage` |

### 1.4 Game State Payload Fields (from `reconstructor.py`)

When a `game_state` event arrives, the payload at `p.p` contains:

| SFS2X Field | Type | Meaning | Our Mapping |
|-------------|------|---------|-------------|
| `gStg` | int | Game stage: 1=BIDDING, 2=PLAYING, 3=TRICK_COMPLETE | `phase` |
| `dealer` | int | **1-indexed** dealer seat | `dealerIndex` (convert to 0-indexed) |
| `mover` | int | **1-indexed** current player seat | `currentTurnIndex` (convert to 0-indexed) |
| `pcs` | int[] | Bitmask-encoded cards per player (4 elements) | `players[i].hand` (decode via card_mapping) |
| `played_cards` | int[] | Cards on table (up to 4 card indices) | `tableCards` |
| `gm` | int | Game mode: 1=SUN, 2=HOKUM | `gameMode` |
| `ts` | int | Trump suit index (0=♠,1=♥,2=♣,3=♦) — for HOKUM | `trumpSuit` |
| `last_action` | str | Last action name (e.g., "bidAction", "a_play") | Used for event classification |
| `ap` | int | **1-indexed** seat that won the trick | Trick winner extraction |
| `pcsCount` | int | Cards remaining per player (resets at 8=new round) | Round boundary detection |
| `sn0..sn3` | str | Player names at seats 0-3 | Player identity |

### 1.5 Card Index Encoding (from `card_mapping.py`)

Source uses a **0-51 card index** system:

```python
# Formula: card_index = suit_index * 13 + rank_index
# Suits:  0=♠, 1=♥, 2=♣, 3=♦
# Ranks:  0=2, 1=3, 2=4, 3=5, 4=6, 5=7, 6=8, 7=9, 8=10, 9=J, 10=Q, 11=K, 12=A
# Baloot only uses ranks 7-A → indices 5-12
# Valid Baloot card indices: 5-12, 18-25, 31-38, 44-51

SUIT_SYMBOLS = {0: '♠', 1: '♥', 2: '♣', 3: '♦'}
RANK_NAMES   = {5:'7', 6:'8', 7:'9', 8:'10', 9:'J', 10:'Q', 11:'K', 12:'A'}
```

Conversion functions in `card_mapping.py`:
- `index_to_card(idx) → Card(suit, rank)` — convert Source index to our Card object
- `card_to_index(card) → int` — convert our Card to Source index
- `decode_bitmask_hand(bitmask) → list[int]` — decode a bitmask integer into card indices

### 1.6 Bitmask Hand Encoding

Player hands in `pcs[]` are **bitmask-encoded integers**. Each bit position corresponds to a card index (0-51). Bit set = player has that card.

```python
def decode_bitmask_hand(bitmask: int) -> list[int]:
    """Decode bitmask to list of card indices."""
    cards = []
    for i in range(52):
        if bitmask & (1 << i):
            cards.append(i)
    return cards
```

### 1.7 Seat Indexing — CRITICAL CONVERSION

Source uses **1-indexed** seats (1,2,3,4). Our engine uses **0-indexed** (0,1,2,3).

```python
# Convert Source seat → Our index
our_index = source_seat - 1

# Positions map (0-indexed):
# 0 = Bottom (our player)
# 1 = Right
# 2 = Top (partner)
# 3 = Left
```

You must identify which seat is "us" via the login/join events. The seat 
where `sn{i}` matches our username is our seat.

---

## Part 2: The `game_state` Dict — Exact Shape BotAgent Expects

The `BotAgent.get_decision(game_state, player_index)` method receives a dict
that must match this schema **exactly**. Read `ai_worker/bot_context.py` and
`game_engine/logic/game.py:get_game_state()` for the canonical definition.

```python
game_state = {
    # ── Identity ──
    "roomId": str,          # Game ID
    "gameId": str,          # Same as roomId (for brain lookups)

    # ── Phase & Mode ──
    "phase": str,           # "BIDDING" | "PLAYING" | "DOUBLING" | "FINISHED"
    "gameMode": str | None, # "SUN" | "HOKUM" | None (before bid resolves)
    "trumpSuit": str | None,# "♠"|"♥"|"♣"|"♦" | None (SUN has no trump)
    "biddingPhase": str | None,  # "FIRST_PASS" etc. if using BiddingEngine
    "biddingRound": int,    # 1 or 2

    # ── Players (MUST be list of 4 dicts) ──
    "players": [
        {
            "hand": [{"suit": "♠", "rank": "A"}, ...],  # Card dicts
            "position": "Bottom",  # "Bottom"|"Right"|"Top"|"Left"
            "name": str,
            "team": "us" | "them",
            "avatar": str,        # Optional
            "profile": str | None, # Optional personality profile
            "difficulty": str | None,  # "EASY"|"MEDIUM"|"HARD"
            "strategy": str | None,    # "heuristic"|"neural"|"mcts"
        },
        # ... 3 more players (Right, Top, Left)
    ],

    # ── Table Cards (cards currently on the table in this trick) ──
    "tableCards": [
        {
            "card": {"suit": "♥", "rank": "K"},
            "playedBy": "Right",    # Position string
            "playerId": str | None, # Optional
            "metadata": dict | None,
        },
        # ... up to 3 more
    ],

    # ── Turn & Dealer ──
    "currentTurnIndex": int,  # 0-3, whose turn it is
    "dealerIndex": int,       # 0-3, who dealt

    # ── Bid State ──
    "bid": {
        "type": "SUN" | "HOKUM" | "ASHKAL" | None,
        "bidder": "Bottom" | "Right" | "Top" | "Left" | None,
        "doubled": bool,
        "suit": str | None,  # Trump suit for HOKUM
        "level": int,        # 1=normal, 2=doubled, 4=re-doubled
        "variant": str | None,
    },

    # ── Scores ──
    "teamScores": {"us": int, "them": int},   # Current round points
    "matchScores": {"us": int, "them": int},  # Overall match points

    # ── Floor Card (shown during bidding) ──
    "floorCard": {"suit": str, "rank": str} | None,

    # ── Trick History (current round) ──
    "currentRoundTricks": [
        {
            "winner": "Bottom",
            "points": int,
            "cards": [
                {"card": {"suit": "♠", "rank": "A"}, "playedBy": "Bottom"},
                # ... up to 3 more
            ],
        },
        # ... previous tricks this round
    ],

    # ── Bid History ──
    "bidHistory": [
        {"player": "Bottom", "action": "SUN", "suit": None},
        {"player": "Right", "action": "PASS", "suit": None},
        # ...
    ],

    # ── Advanced State ──
    "strictMode": True,       # Bots must play legal moves
    "trickCount": int,        # Number of completed tricks
    "doublingLevel": int,     # 1, 2, or 4
    "isLocked": bool,
    "qaydState": {},          # Qayd challenge state
    "sawaState": {},          # Sawa declaration state
    "akkaState": None | {},   # Akka state
    "declarations": {},       # Projects (Baloot, Sira, etc.)
}
```

### BotAgent Decision Output Format

`BotAgent.get_decision()` returns one of:

```python
# Playing phase:
{"action": "PLAY", "cardIndex": 2, "reasoning": "..."}

# Bidding phase:
{"action": "SUN" | "HOKUM" | "PASS", "suit": "♠" | None, "reasoning": "..."}

# Fallback:
{"action": "PASS"}
```

The `cardIndex` is the **index into `players[my_index].hand`** list, NOT the Source
card index. So if hand = [7♠, 9♥, A♦] and decision says cardIndex=2, it means play A♦.

---

## Part 3: Implementation — `StateBuilder` (NEW)

**File**: `gbaloot/core/state_builder.py`

This is the **hardest module**. It must maintain a running `game_state` dict
that is always valid for BotAgent consumption.

### 3.1 Initialization

```python
class StateBuilder:
    def __init__(self, my_username: str):
        self.my_username = my_username
        self.my_seat = None          # 0-indexed, discovered from login events
        self.game_state = self._empty_state()
        self._trick_history = []
        self._bid_history = []

    def _empty_state(self) -> dict:
        """Return a blank game_state dict with all required keys."""
        return {
            "roomId": "gbaloot_live",
            "gameId": "gbaloot_live",
            "phase": None,
            "gameMode": None,
            "trumpSuit": None,
            "biddingPhase": None,
            "biddingRound": 1,
            "players": [
                {"hand": [], "position": pos, "name": f"Player_{i}",
                 "team": "us" if i % 2 == 0 else "them",
                 "avatar": "bot_1"}
                for i, pos in enumerate(["Bottom","Right","Top","Left"])
            ],
            "tableCards": [],
            "currentTurnIndex": 0,
            "dealerIndex": 0,
            "bid": {"type": None, "bidder": None, "doubled": False},
            "teamScores": {"us": 0, "them": 0},
            "matchScores": {"us": 0, "them": 0},
            "floorCard": None,
            "currentRoundTricks": [],
            "bidHistory": [],
            "strictMode": True,
            "trickCount": 0,
            "doublingLevel": 1,
            "isLocked": False,
        }
```

### 3.2 Event Processing — THE CORE LOGIC

Process each SFS2X decoded event. The key is the `fields.p.p` nesting:

```python
def process_event(self, event: dict):
    """Process a single decoded GameEvent dict.

    The event dict has:
      timestamp, direction, action, fields, raw_size
    """
    action = event.get("action", "")
    fields = event.get("fields", {})

    # Extract the game payload (nested p→p structure)
    payload = fields
    if "p" in fields and isinstance(fields["p"], dict):
        payload = fields["p"]
        if "p" in payload and isinstance(payload["p"], dict):
            payload = payload["p"]

    # === IDENTITY DISCOVERY ===
    if action in ("onLogin", "onUserEnter", "ws_connect"):
        self._discover_identity(payload)

    # === GAME STATE UPDATE ===
    if action in ("game_state", "a_game_state_change"):
        self._process_game_state(payload)

    # === CARD PLAY ===
    elif action in ("a_play", "cardPlayed", "playCard"):
        self._process_card_play(payload)

    # === TRICK WON ===
    elif action in ("a_cards_eating", "trickWon", "eatCards"):
        self._process_trick_won(payload)

    # === BIDDING ===
    elif action in ("bidAction", "a_start_bid"):
        self._process_bid(payload)

    # === BID END ===
    elif action in ("endBid",):
        self._process_bid_end(payload)

    # === DEAL ===
    elif action == "deal":
        self._process_deal(payload)

    # === ROUND END ===
    elif action in ("endGame", "gameResult", "roundOver"):
        self._process_round_end(payload)
```

### 3.3 Key Processing Methods

#### Identity Discovery

```python
def _discover_identity(self, payload: dict):
    """Find which seat we are by matching username to sn0..sn3."""
    for i in range(4):
        name_key = f"sn{i}"
        if name_key in payload:
            if payload[name_key] == self.my_username:
                self.my_seat = i
                # Remap positions so WE are always "Bottom" (index 0 in BotAgent)
                self._remap_positions(i)
```

#### Game State Processing (the big one)

```python
def _process_game_state(self, payload: dict):
    """Translate SFS2X game_state payload → BotAgent game_state dict."""
    from gbaloot.core.card_mapping import (
        index_to_card, decode_bitmask_hand, suit_idx_to_symbol, map_game_mode
    )

    # Game stage → phase
    gStg = payload.get("gStg")
    if gStg == 1:
        self.game_state["phase"] = "BIDDING"
    elif gStg == 2:
        self.game_state["phase"] = "PLAYING"
    elif gStg == 3:
        self.game_state["phase"] = "PLAYING"  # Trick complete, still PLAYING phase

    # Game mode
    gm = payload.get("gm")
    if gm is not None:
        self.game_state["gameMode"] = map_game_mode(gm)  # 1→"SUN", 2→"HOKUM"

    # Trump suit (HOKUM only)
    ts = payload.get("ts")
    if ts is not None and self.game_state["gameMode"] == "HOKUM":
        self.game_state["trumpSuit"] = suit_idx_to_symbol(ts)
    elif self.game_state["gameMode"] == "SUN":
        self.game_state["trumpSuit"] = None

    # Dealer & mover (1-indexed → 0-indexed, then REMAP to our perspective)
    dealer = payload.get("dealer")
    if dealer is not None:
        self.game_state["dealerIndex"] = self._remap_seat(dealer - 1)

    mover = payload.get("mover")
    if mover is not None:
        self.game_state["currentTurnIndex"] = self._remap_seat(mover - 1)

    # Player hands (bitmask decode)
    pcs = payload.get("pcs")
    if pcs and isinstance(pcs, list) and len(pcs) == 4:
        for src_seat in range(4):
            our_idx = self._remap_seat(src_seat)
            card_indices = decode_bitmask_hand(pcs[src_seat])
            hand = []
            for ci in card_indices:
                card = index_to_card(ci)
                if card:
                    hand.append({"suit": card.suit, "rank": card.rank})
            self.game_state["players"][our_idx]["hand"] = hand

    # Table cards
    played = payload.get("played_cards")
    if played and isinstance(played, list):
        table = []
        positions = ["Bottom", "Right", "Top", "Left"]
        for src_seat, ci in enumerate(played):
            if ci and ci > 0:  # 0 or -1 means no card
                card = index_to_card(ci)
                if card:
                    our_idx = self._remap_seat(src_seat)
                    table.append({
                        "card": {"suit": card.suit, "rank": card.rank},
                        "playedBy": positions[our_idx],
                        "playerId": None,
                        "metadata": None,
                    })
        self.game_state["tableCards"] = table
```

#### Seat Remapping — Critical!

```python
def _remap_seat(self, source_seat_0indexed: int) -> int:
    """Convert Source 0-indexed seat to our perspective (where WE are index 0).

    If we are seat 2 in Source, then:
      Source seat 2 → Our index 0 (Bottom, us)
      Source seat 3 → Our index 1 (Right)
      Source seat 0 → Our index 2 (Top, partner)
      Source seat 1 → Our index 3 (Left)
    """
    if self.my_seat is None:
        return source_seat_0indexed
    return (source_seat_0indexed - self.my_seat) % 4
```

### 3.4 Turn Detection

```python
def is_my_turn(self) -> bool:
    """Check if it's our turn to act."""
    if self.game_state["phase"] not in ("BIDDING", "PLAYING", "DOUBLING"):
        return False
    return self.game_state["currentTurnIndex"] == 0  # We are always index 0
```

---

## Part 4: Implementation — `GBoard` via JavaScript Injection (NEW)

**File**: `gbaloot/core/gboard.py`

**THIS IS THE CORE FOCUS.** The GBoard must interact with the game by
**reverse-engineering the game's internal JavaScript objects** and invoking
their methods directly via `page.evaluate()`. No pixel clicking. No DOM selectors.
source platform renders to a `<canvas>` element using a JS game framework.

### 4.1 Why JS Injection Is The Only Reliable Strategy

source platform is a **canvas/WebGL game** — there are NO `<div data-card="...">` elements
to click. The entire game board is painted onto a single `<canvas>`. This means:

- **DOM selectors don't work** — there is nothing to `.querySelector()` for cards
- **Pixel clicking is fragile** — coordinates change with window size, resolution,
  and animation state. Cards slide, fan, highlight. A 3px miscalibration = wrong card.
- **JS injection is deterministic** — once you find the game's internal card play
  function, calling it works every time regardless of screen size or animation state.

### 4.2 Phase 1: Reconnaissance — Discover the Game Framework

Before writing any actuator code, you MUST reverse-engineer the game's JavaScript.
Use Playwright's `page.evaluate()` to probe the browser environment.

#### Step 1: Identify the Framework

```python
# Run this in Playwright to discover what game framework is being used:
framework_info = await page.evaluate("""
    () => {
        const result = {};
        // Check for common game frameworks
        if (window.Phaser) result.phaser = Phaser.VERSION || true;
        if (window.PIXI) result.pixi = PIXI.VERSION || true;
        if (window.createjs) result.createjs = true;
        if (window.cc) result.cocos = true;              // Cocos2d
        if (window.Laya) result.laya = true;              // LayaAir
        if (window.egret) result.egret = true;            // Egret
        if (window.THREE) result.three = THREE.REVISION || true;
        if (window.BABYLON) result.babylon = true;
        // Check for SFS2X client
        if (window.SFS2X) result.sfs2x = true;
        if (window.SmartFox) result.smartfox = true;
        // Check for game-specific globals
        result.windowKeys = Object.keys(window).filter(k =>
            !['chrome','webkitStorageInfo','performance'].includes(k) &&
            typeof window[k] === 'object' && window[k] !== null
        ).slice(0, 50);
        return result;
    }
""")
```

#### Step 2: Find the Game Application Object

```python
# Probe for the game's main application/scene object:
game_objects = await page.evaluate("""
    () => {
        const result = {};

        // === Phaser-style ===
        if (window.Phaser) {
            // Phaser games usually store the instance
            const canvas = document.querySelector('canvas');
            if (canvas && canvas.__phaser) result.phaser_instance = true;
            // Check for global game variable
            for (const key of Object.keys(window)) {
                const val = window[key];
                if (val && val.scene && val.scene.scenes) {
                    result.game_var = key;
                    result.scenes = val.scene.scenes.map(s => s.constructor.name);
                    break;
                }
            }
        }

        // === PIXI-style ===
        if (window.PIXI) {
            for (const key of Object.keys(window)) {
                const val = window[key];
                if (val instanceof PIXI.Application) {
                    result.pixi_app = key;
                    break;
                }
            }
        }

        // === Generic: Find game-like objects ===
        for (const key of Object.keys(window)) {
            const val = window[key];
            if (val && typeof val === 'object') {
                const props = Object.keys(val);
                // Look for game-specific properties
                if (props.some(p => ['playCard','onCardClick','cardClicked',
                    'sendPlay','doPlay','handlePlay'].includes(p))) {
                    result.game_controller = key;
                    result.game_methods = props.filter(p => typeof val[p] === 'function');
                }
            }
        }

        return result;
    }
""")
```

#### Step 3: Hunt for Card Play Functions

This is the **most important step**. You need to find JavaScript functions that:
1. Accept a card identifier (index, object, or suit+rank)
2. Send the play command to the SFS2X server

```python
# Deep scan for card-play related functions anywhere in the global scope:
card_functions = await page.evaluate("""
    () => {
        const found = [];

        function scanObj(obj, path, depth) {
            if (depth > 4 || !obj || typeof obj !== 'object') return;
            try {
                for (const key of Object.getOwnPropertyNames(obj)) {
                    try {
                        const val = obj[key];
                        const fullPath = path + '.' + key;

                        if (typeof val === 'function') {
                            const src = val.toString().substring(0, 200);
                            // Look for functions that mention card playing
                            if (/play|card|send|click|select|bid|trump/i.test(key) ||
                                /playCard|sendExtension|a_play/i.test(src)) {
                                found.push({
                                    path: fullPath,
                                    name: key,
                                    argsCount: val.length,
                                    snippet: src
                                });
                            }
                        }
                        // Recurse into sub-objects (but skip DOM, Window, etc.)
                        else if (typeof val === 'object' && val !== null &&
                                 !(val instanceof HTMLElement) &&
                                 !(val instanceof Window)) {
                            scanObj(val, fullPath, depth + 1);
                        }
                    } catch(e) {}
                }
            } catch(e) {}
        }

        // Scan common game namespaces
        for (const key of Object.keys(window)) {
            try {
                const val = window[key];
                if (val && typeof val === 'object' && val !== null) {
                    scanObj(val, key, 0);
                }
            } catch(e) {}
        }

        return found;
    }
""")
```

#### Step 4: Find the SFS2X Client and Send Commands Directly

The game communicates with the server via SFS2X. If you can find the SFS2X client
object, you can send extension requests directly — bypassing the UI entirely.

```python
# Find the SFS2X SmartFox client instance:
sfs_client = await page.evaluate("""
    () => {
        const result = {};

        function findSFS(obj, path, depth) {
            if (depth > 5 || !obj || typeof obj !== 'object') return;
            try {
                for (const key of Object.getOwnPropertyNames(obj)) {
                    try {
                        const val = obj[key];
                        const fullPath = path + '.' + key;

                        // SFS2X client objects have distinct signatures
                        if (val && typeof val === 'object') {
                            // Check for SmartFox instance properties
                            if (val.send && val.addEventListener &&
                                (val._socketEngine || val.sessionToken || val.currentZone)) {
                                result.sfs_path = fullPath;
                                result.methods = Object.getOwnPropertyNames(val)
                                    .filter(k => typeof val[k] === 'function');
                                return;
                            }
                            // Check for SFS2X API namespace (has Request constructors)
                            if (val.ExtensionRequest || val.LoginRequest) {
                                result.sfs_api_path = fullPath;
                            }
                        }
                        if (depth < 4 && val && typeof val === 'object' &&
                            !(val instanceof HTMLElement)) {
                            findSFS(val, fullPath, depth + 1);
                        }
                    } catch(e) {}
                }
            } catch(e) {}
        }

        for (const key of Object.keys(window)) {
            try { findSFS(window[key], key, 0); } catch(e) {}
            if (result.sfs_path) break;
        }

        return result;
    }
""")
```

### 4.3 Phase 2: Build the GBoard Using Discovered APIs

Once you've discovered the game's internal API, implement `GBoard` using those
objects. Below are **template patterns** — adapt based on what the recon reveals.

#### Pattern A: Direct Game Controller Call

If you find a game controller with a `playCard()` method:

```python
class GBoard:
    """Actuator via JS injection into the game's internal API."""

    def __init__(self, page):
        self.page = page
        # These paths are discovered during recon and stored here
        self.game_controller_path = None    # e.g., "window.game.controller"
        self.sfs_client_path = None         # e.g., "window.__sfs"
        self._initialized = False

    async def initialize(self):
        """Run reconnaissance to discover game internals.
        
        This MUST be called after the game has loaded and a round has started.
        """
        # Discover the framework and game objects
        recon = await self._run_recon()

        if recon.get("game_controller"):
            self.game_controller_path = recon["game_controller"]
        if recon.get("sfs_path"):
            self.sfs_client_path = recon["sfs_path"]

        self._initialized = True
        return recon

    async def execute(self, decision: dict, game_state: dict):
        """Execute a BotAgent decision by calling game internals."""
        action = decision.get("action")

        if action == "PLAY":
            card_index = decision["cardIndex"]
            hand = game_state["players"][0]["hand"]
            card = hand[card_index]
            await self._play_card(card)
        elif action in ("SUN", "HOKUM", "PASS", "DOUBLE"):
            await self._submit_bid(action, decision.get("suit"))

    async def _play_card(self, card: dict):
        """Play a card by invoking the game's card play function.

        The `card` dict has: {"suit": "♠", "rank": "A"}
        We must convert this to whatever the game framework expects.
        """
        suit = card["suit"]
        rank = card["rank"]

        # Convert our card representation to the Source card index
        # (needed to call the game's internal API)
        source_card_index = await self.page.evaluate(f"""
            () => {{
                const SUITS = {{'♠': 0, '♥': 1, '♣': 2, '♦': 3}};
                const RANKS = {{'7': 5, '8': 6, '9': 7, '10': 8,
                               'J': 9, 'Q': 10, 'K': 11, 'A': 12}};
                return SUITS['{suit}'] * 13 + RANKS['{rank}'];
            }}
        """)

        # === OPTION 1: Call the game's playCard function directly ===
        if self.game_controller_path:
            await self.page.evaluate(f"""
                () => {{
                    const controller = {self.game_controller_path};
                    // Adapt this call based on what the recon discovers.
                    // Possible signatures:
                    //   controller.playCard(cardIndex)
                    //   controller.onCardClick(cardObj)
                    //   controller.sendPlay(suitIdx, rankIdx)
                    controller.playCard({source_card_index});
                }}
            """)
            return

        # === OPTION 2: Construct and send an SFS2X ExtensionRequest ===
        if self.sfs_client_path:
            await self._send_sfs_extension("a_play", {
                "card": source_card_index,
            })
            return

        raise RuntimeError("GBoard not initialized — no game API found")

    async def _submit_bid(self, action: str, suit: str | None = None):
        """Submit a bid by calling the game's bid function."""
        bid_map = {
            "SUN": 1,       # Adapt based on what the game expects
            "HOKUM": 2,
            "PASS": 0,
            "DOUBLE": 3,
        }
        bid_value = bid_map.get(action, 0)

        suit_map = {"♠": 0, "♥": 1, "♣": 2, "♦": 3}
        suit_index = suit_map.get(suit, -1) if suit else -1

        if self.game_controller_path:
            await self.page.evaluate(f"""
                () => {{
                    const controller = {self.game_controller_path};
                    // Adapt: controller.submitBid(bidValue, suitIndex)
                    controller.submitBid({bid_value}, {suit_index});
                }}
            """)
        elif self.sfs_client_path:
            params = {"bid": bid_value}
            if suit_index >= 0:
                params["ts"] = suit_index
            await self._send_sfs_extension("bidAction", params)

    async def _send_sfs_extension(self, cmd: str, params: dict):
        """Send a raw SFS2X ExtensionRequest — the nuclear option.

        This bypasses the game UI entirely and talks to the server directly.
        Use this if you can't find the game's play/bid functions but CAN
        find the SmartFox client instance.
        """
        import json
        params_json = json.dumps(params)

        await self.page.evaluate(f"""
            () => {{
                const sfs = {self.sfs_client_path};
                const SFSObject = SFS2X.Entities.Data.SFSObject || window.SFS2X?.Entities?.Data?.SFSObject;

                if (!sfs || !SFSObject) {{
                    console.error('GBoard: SFS client or SFSObject not found');
                    return;
                }}

                const obj = new SFSObject();
                const params = {params_json};
                for (const [key, val] of Object.entries(params)) {{
                    if (typeof val === 'number') obj.putInt(key, val);
                    else if (typeof val === 'string') obj.putUtfString(key, val);
                    else if (typeof val === 'boolean') obj.putBool(key, val);
                }}

                const req = new SFS2X.Requests.System.ExtensionRequest('{cmd}', obj, sfs.lastJoinedRoom);
                sfs.send(req);
            }}
        """)
```

#### Pattern B: Event Dispatching on Canvas

If recon reveals the framework uses event listeners on the canvas, you can
dispatch synthetic pointer events at the card's coordinates within the game world:

```python
async def _dispatch_card_event(self, card_game_obj_path: str):
    """Dispatch a click event on a game object (Phaser/PIXI style)."""
    await self.page.evaluate(f"""
        () => {{
            const cardObj = {card_game_obj_path};
            if (cardObj && cardObj.emit) {{
                // Phaser/PIXI style: emit pointer events
                cardObj.emit('pointerdown');
                setTimeout(() => cardObj.emit('pointerup'), 50);
            }} else if (cardObj && cardObj.dispatchEvent) {{
                cardObj.dispatchEvent(new Event('click'));
            }}
        }}
    """)
```

### 4.4 Phase 3: Recon Automation Script

Create a standalone recon script that Claude runs FIRST to discover everything:

**File**: `gbaloot/core/gboard_recon.py`

```python
"""
GBoard Reconnaissance Script.

Run this while a game is active in the browser to discover:
  1. Which game framework is used
  2. Where the game controller / scene objects live
  3. What card-play and bid functions exist
  4. Where the SFS2X client instance is

Output: a JSON report that GBoard uses to initialize.
"""

import asyncio
import json
import logging

logger = logging.getLogger(__name__)

RECON_SCRIPTS = {
    "framework": """() => {
        const r = {};
        if (window.Phaser) r.phaser = Phaser.VERSION || '?';
        if (window.PIXI) r.pixi = PIXI.VERSION || '?';
        if (window.createjs) r.createjs = true;
        if (window.cc) r.cocos = true;
        if (window.Laya) r.laya = true;
        if (window.egret) r.egret = true;
        if (window.SFS2X) r.sfs2x_api = true;
        if (window.SmartFox) r.smartfox = true;
        r.canvas_count = document.querySelectorAll('canvas').length;
        return r;
    }""",

    "global_game_objects": """() => {
        const found = [];
        const skip = new Set(['chrome','__coverage__','webkitStorageInfo',
            'performance','caches','cookieStore','scheduler']);
        for (const key of Object.keys(window)) {
            if (skip.has(key)) continue;
            try {
                const val = window[key];
                if (val && typeof val === 'object' && val !== null &&
                    !(val instanceof HTMLElement) && !(val instanceof Window)) {
                    const keys = Object.keys(val).slice(0, 20);
                    const funcs = keys.filter(k => typeof val[k] === 'function');
                    if (funcs.length > 2) {
                        found.push({ name: key, keys: keys, funcs: funcs });
                    }
                }
            } catch(e) {}
        }
        return found.slice(0, 30);
    }""",

    "card_play_functions": """() => {
        const found = [];
        const pattern = /play|card|send|select|bid|trump|click/i;

        function scan(obj, path, depth) {
            if (depth > 3 || !obj) return;
            try {
                for (const key of Object.getOwnPropertyNames(obj)) {
                    try {
                        const val = obj[key];
                        const fp = path + '.' + key;
                        if (typeof val === 'function' && pattern.test(key)) {
                            found.push({
                                path: fp, name: key, args: val.length,
                                src: val.toString().substring(0, 300)
                            });
                        } else if (depth < 3 && val && typeof val === 'object' &&
                                   !(val instanceof HTMLElement) &&
                                   !(val instanceof Window)) {
                            scan(val, fp, depth + 1);
                        }
                    } catch(e) {}
                }
            } catch(e) {}
        }

        for (const key of Object.keys(window)) {
            try {
                const val = window[key];
                if (val && typeof val === 'object') scan(val, key, 0);
            } catch(e) {}
            if (found.length > 50) break;
        }
        return found;
    }""",

    "sfs_client": """() => {
        const result = {};
        function find(obj, path, d) {
            if (d > 4 || !obj) return false;
            try {
                for (const k of Object.getOwnPropertyNames(obj)) {
                    try {
                        const v = obj[k]; const fp = path + '.' + k;
                        if (v && v.send && v.addEventListener &&
                            (v._socketEngine || v.sessionToken || v.currentZone)) {
                            result.path = fp;
                            result.methods = Object.getOwnPropertyNames(v)
                                .filter(m => typeof v[m] === 'function').slice(0, 30);
                            result.zone = v.currentZone;
                            result.room = v.lastJoinedRoom?.name;
                            return true;
                        }
                        if (d < 4 && v && typeof v === 'object' &&
                            !(v instanceof HTMLElement)) {
                            if (find(v, fp, d + 1)) return true;
                        }
                    } catch(e) {}
                }
            } catch(e) {}
            return false;
        }
        for (const k of Object.keys(window)) {
            try { if (find(window[k], k, 0)) break; } catch(e) {}
        }
        return result;
    }""",

    "websocket_instances": """() => {
        // Check for stored WebSocket references
        const result = {};
        if (window.__ws_original) result.intercepted = true;
        // Count active WebSocket connections
        result.readyStates = [];
        // Check if we can find the WS via the SFS engine
        return result;
    }""",

    "event_listeners_on_canvas": """() => {
        const canvas = document.querySelector('canvas');
        if (!canvas) return { error: 'No canvas found' };
        // Try to extract event listener info
        const result = { id: canvas.id, classes: canvas.className };
        // Chrome DevTools API (may not always be available)
        if (typeof getEventListeners === 'function') {
            const listeners = getEventListeners(canvas);
            result.listeners = Object.keys(listeners);
        }
        return result;
    }"""
}


async def run_full_recon(page) -> dict:
    """Run all reconnaissance scripts and return a combined report."""
    report = {}
    for name, script in RECON_SCRIPTS.items():
        try:
            result = await page.evaluate(script)
            report[name] = result
            logger.info(f"Recon [{name}]: {json.dumps(result, default=str)[:200]}")
        except Exception as e:
            report[name] = {"error": str(e)}
            logger.warning(f"Recon [{name}] failed: {e}")
    return report


async def save_recon_report(page, output_path: str = "gbaloot/recon_report.json"):
    """Run recon and save to a JSON file for analysis."""
    report = await run_full_recon(page)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"Recon report saved to {output_path}")
    return report
```

### 4.5 The Recon → Build Workflow

The GBoard development is a **two-phase process**:

```
PHASE 1: RECON (human-in-the-loop)
  1. Open source platform in Playwright (headful mode)
  2. Join a game, wait for cards to be dealt
  3. Run `save_recon_report(page)` → gbaloot/recon_report.json
  4. READ the report carefully
  5. Based on what you find, write MORE targeted probes:
     - If Phaser: probe `game.scene.scenes[0]` children
     - If PIXI: probe `app.stage.children` recursively
     - If raw canvas: look for event handler registrations
     - If SFS2X client found: try sending a test command
  6. Iterate until you have:
     ✅ The path to the card play function OR
     ✅ The path to the SFS2X client for direct commands

PHASE 2: BUILD (once APIs are found)
  1. Implement GBoard with the discovered paths
  2. Test each action individually (play card, bid)
  3. Wire into AutopilotSession
```

### 4.6 Fallback: Direct SFS2X Protocol Commands

If the game framework is obfuscated beyond reverse-engineering, you can ALWAYS
fall back to sending SFS2X extension requests directly. The protocol is well-known:

```python
# The nuclear fallback — send commands directly to the SFS2X server.
# This bypasses the client-side game logic entirely.

# Playing a card:
await gboard._send_sfs_extension("a_play", {"card": source_card_index})

# Submitting a bid:
await gboard._send_sfs_extension("bidAction", {"bid": 1, "ts": 0})  # SUN bid
await gboard._send_sfs_extension("bidAction", {"bid": 2, "ts": 2})  # HOKUM ♣
await gboard._send_sfs_extension("bidAction", {"bid": 0})            # PASS
```

> **WARNING**: The exact command names and parameter names MUST be verified
> by watching actual outgoing WS messages during manual play. Use the existing
> `GameCapturer` to capture a session, then inspect the `direction: "outgoing"`
> events to see exactly what the client sends when you play a card or bid.

### 4.7 Discovering Outgoing Message Format

To know what SFS2X commands the game sends, capture a manual play session:

```python
# In capture_session.py, the interceptor already captures BOTH directions.
# After a manual game, inspect the session JSON for outgoing messages:
#
# Look for events where direction == "outgoing" and action matches:
#   - Card play: look for "a_play" or similar
#   - Bid: look for "bidAction" or similar
#   - Any other user action
#
# The payload of these outgoing messages reveals the exact format
# the server expects. Copy that format into GBoard._send_sfs_extension().
```

---

## Part 5: Implementation — `AutopilotSession` (NEW)

**File**: `gbaloot/autopilot.py`

### 5.1 Main Loop

```python
import asyncio
import logging
import time
from gbaloot.core.decoder import SFS2XDecoder
from gbaloot.core.state_builder import StateBuilder
from gbaloot.core.gboard import GBoard

logger = logging.getLogger(__name__)

class AutopilotSession:
    """Main autopilot orchestrator."""

    def __init__(self, page, username: str):
        self.page = page
        self.decoder = SFS2XDecoder()
        self.state_builder = StateBuilder(my_username=username)
        self.gboard = GBoard(page)
        self.running = True
        self._message_buffer = []

        # Safety
        self.min_action_delay = 2.0   # Seconds between actions (human-like)
        self.last_action_time = 0

    async def start(self):
        """Inject WS interceptor, run recon, and start the autopilot loop."""
        # Step 1: Inject the existing WS interceptor from capturer.py
        from gbaloot.core.capturer import WS_INTERCEPTOR_JS
        await self.page.evaluate(WS_INTERCEPTOR_JS)

        # Step 2: Run GBoard reconnaissance to discover game internals
        logger.info("Running GBoard reconnaissance...")
        recon = await self.gboard.initialize()
        logger.info(f"Recon complete: {recon}")

        if not self.gboard._initialized:
            logger.error("GBoard recon failed — cannot find game API. Aborting.")
            return

        logger.info("Autopilot started. Waiting for game events...")
        await self._loop()

    async def _loop(self):
        """Main event loop."""
        while self.running:
            # 0. Kill switch check
            if await self._check_kill_switch():
                await asyncio.sleep(1.0)
                continue

            # 1. Collect new intercepted messages
            messages = await self._collect_messages()

            # 2. Decode and process each message
            for msg in messages:
                try:
                    decoded = self.decoder.decode_message(msg["data"])
                    if decoded:
                        event = self.decoder.classify_event(decoded, msg["direction"])
                        self.state_builder.process_event(event)
                except Exception as e:
                    logger.debug(f"Decode error: {e}")

            # 3. Check if it's our turn
            if self.state_builder.is_my_turn():
                await self._act()

            await asyncio.sleep(0.1)  # 100ms poll interval

    async def _collect_messages(self) -> list:
        """Pull intercepted WS messages from the browser."""
        try:
            messages = await self.page.evaluate("""
                () => {
                    const msgs = window.__ws_messages || [];
                    window.__ws_messages = [];
                    return msgs;
                }
            """)
            return messages or []
        except Exception:
            return []

    async def _act(self):
        """Get a decision from BotAgent and execute it."""
        # Rate limiting
        now = time.time()
        if now - self.last_action_time < self.min_action_delay:
            return

        try:
            from ai_worker.agent import bot_agent

            gs = self.state_builder.game_state
            decision = bot_agent.get_decision(gs, player_index=0)

            if decision and decision.get("action") != "PASS":
                await self.gboard.execute(decision, gs)
                self.last_action_time = time.time()

                logger.info(
                    f"ACTION: {decision.get('action')} "
                    f"cardIndex={decision.get('cardIndex')} "
                    f"reason={decision.get('reasoning', '')[:60]}"
                )
        except Exception as e:
            logger.error(f"Autopilot decision error: {e}")

    async def _check_kill_switch(self) -> bool:
        """Pause if kill switch is engaged."""
        from pathlib import Path
        return Path("gbaloot/.pause").exists()
```

### 5.2 Integrating with `capture_session.py`

Add an `--autopilot` flag to the existing capture session:

```python
# In capture_session.py, add to argparse:
parser.add_argument("--autopilot", action="store_true",
                    help="Enable autopilot mode (bot plays for you)")
parser.add_argument("--username", type=str,
                    help="Your source platform username (for seat detection)")

# In the main session loop, after page is ready:
if args.autopilot:
    from gbaloot.autopilot import AutopilotSession
    autopilot = AutopilotSession(page, username=args.username)
    await autopilot.start()
```

---

## Part 6: Safety & Edge Cases

### 6.1 Kill Switch
```python
# In AutopilotSession:
async def _check_kill_switch(self) -> bool:
    """Pause if user wants to take over."""
    # Option A: Check a flag file (touch gbaloot/.pause to pause)
    # Option B: Detect mouse movement on the game canvas
    # Option C: Listen for a hotkey (Ctrl+Shift+P to pause)
    from pathlib import Path
    return Path("gbaloot/.pause").exists()
```

### 6.2 Edge Cases to Handle

| Scenario | How to Handle |
|----------|---------------|
| We don't know our seat yet | Skip `_act()` until `my_seat` is discovered |
| Empty hand after decode | Don't call BotAgent (would crash on empty hand) |
| Game between rounds | Detect FINISHED phase, possibly click "Next Round" |
| Disconnection | Detect `ws_disconnect`, attempt reconnect or pause |
| Trump suit selection (HOKUM) | If bidder is us, we need to pick a suit via GBoard |
| Sawa / Akka / Qayd prompts | Auto-decline by default (or wire to BotAgent) |
| Game obfuscation update | Re-run recon, update GBoard paths |

### 6.3 Timing Considerations

- SFS2X events arrive **before** animations complete
- Wait for animations to finish before acting (add 500ms-1s delay after trick_won)
- The `min_action_delay` prevents the bot from looking inhuman

---

## Part 7: File Manifest

| # | File | Status | Size |
|---|------|--------|------|
| 1 | `gbaloot/core/state_builder.py` | **CREATE** | ~200 lines |
| 2 | `gbaloot/core/gboard.py` | **CREATE** | ~200 lines |
| 3 | `gbaloot/core/gboard_recon.py` | **CREATE** | ~150 lines |
| 4 | `gbaloot/autopilot.py` | **CREATE** | ~150 lines |
| 5 | `gbaloot/capture_session.py` | **MODIFY** | +20 lines (add --autopilot flag) |

### Dependencies (Already Exist — DO NOT Rewrite)

- `gbaloot/core/decoder.py` — Full SFS2X binary decoder 
- `gbaloot/core/capturer.py` — WS interceptor JavaScript
- `gbaloot/core/card_mapping.py` — Card index ↔ Card conversion
- `gbaloot/core/event_types.py` — Event classification
- `gbaloot/core/reconstructor.py` — Reference for field names (NOT used at runtime)
- `ai_worker/agent.py` — BotAgent (the brain)
- `ai_worker/bot_context.py` — BotContext (parses game_state dict)

---

## Part 8: Testing the Autopilot

### 8.1 Unit Test: StateBuilder

```python
# Test that a game_state SFS2X payload is correctly translated
def test_state_builder_game_state():
    sb = StateBuilder(my_username="TestUser")
    sb.my_seat = 2  # We are seat 2 in Source

    # Simulate a game_state event
    event = {
        "action": "game_state",
        "fields": {"p": {"p": {
            "gStg": 2,  # PLAYING
            "gm": 1,    # SUN
            "dealer": 1, # Source seat 1 (0-indexed: 0)
            "mover": 3,  # Source seat 3 (0-indexed: 2) = US!
            "pcs": [0, 0, 0b111100000000000000000, 0],  # Some cards for seat 2
        }}}
    }
    sb.process_event(event)

    assert sb.game_state["phase"] == "PLAYING"
    assert sb.game_state["gameMode"] == "SUN"
    assert sb.game_state["currentTurnIndex"] == 0  # Remapped: Source seat 2 → Our 0
    assert sb.is_my_turn() == True
```

### 8.2 GBoard Recon Test (Live Browser)

```python
# Run this with a live source platform session in the browser:
async def test_gboard_recon(page):
    from gbaloot.core.gboard_recon import run_full_recon

    report = await run_full_recon(page)

    # At minimum we should find:
    assert report["framework"]  # Should identify Phaser/PIXI/etc.
    assert report["card_play_functions"]  # Should find card-related functions

    # If SFS2X client found, try a handshake
    if report.get("sfs_client", {}).get("path"):
        print(f"SFS2X client at: {report['sfs_client']['path']}")
        print(f"Methods: {report['sfs_client'].get('methods', [])}")
```

### 8.3 Integration Test: Full Loop (Offline)

Use a saved capture session JSON to replay events through StateBuilder
and verify that the game_state is always valid for BotAgent:

```python
def test_replay_session():
    from gbaloot.core.models import ProcessedSession

    session = ProcessedSession.load("gbaloot/sessions/test_session_processed.json")
    sb = StateBuilder(my_username="the_player_name")

    for event in session.events:
        sb.process_event(event)
        # Verify hand is never empty during PLAYING phase
        if sb.game_state["phase"] == "PLAYING":
            assert len(sb.game_state["players"][0]["hand"]) > 0
```

---

## Quick Reference Cheat Sheet

```
Source "pcs[i]"  →  decode_bitmask_hand()  →  [card_indices]  →  index_to_card()  →  Card(suit, rank)
Source "gm=1"    →  "SUN"     Source "gm=2"  →  "HOKUM"
Source "ts=0"    →  "♠"       Source "ts=1"   →  "♥"       Source "ts=2" → "♣"   Source "ts=3" → "♦"
Source "dealer=3"→  0-indexed: 2  →  remapped: (2 - my_seat) % 4
Source "mover=1" →  0-indexed: 0  →  remapped: (0 - my_seat) % 4
Source "gStg=1"  →  "BIDDING"   Source "gStg=2" → "PLAYING"   Source "gStg=3" → trick complete
BotAgent output  →  {action: "PLAY", cardIndex: N}  →  GBoard converts to Source card index → JS inject
```

---

## Execution Priority

```
1. RUN RECON FIRST  →  gboard_recon.py in a live game session
2. ANALYZE REPORT   →  Read gbaloot/recon_report.json
3. BUILD GBOARD     →  Wire discovered API paths into GBoard
4. BUILD STATE      →  Implement StateBuilder (can be done in parallel)
5. WIRE AUTOPILOT   →  AutopilotSession ties everything together
6. TEST             →  Unit tests → Recon tests → Live integration
```
