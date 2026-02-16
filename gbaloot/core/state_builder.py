"""
StateBuilder — Translates SFS2X decoded events into the game_state dict
that BotAgent.get_decision() expects.

Maintains a running game_state by applying each decoded event incrementally.
Handles seat remapping so that OUR seat is always player index 0 ("Bottom").

Key SFS2X fields:
    gStg          → game stage (1=BIDDING, 2=PLAYING, 3=TRICK_COMPLETE)
    dealer/mover  → 1-indexed seats
    pcs           → bitmask-encoded hand (int per player OR single int)
    played_cards  → 4-element array of card indices (-1 = empty)
    gm            → game mode (str: 'sun'/'hokum' OR int: 1/2)
    ts            → trump suit index (0=♠, 1=♥, 2=♣, 3=♦)
    ss            → 4-element score array
    last_action   → {action, ap, bt} dict
    pcsCount      → 4-element cards-remaining array
    mn            → trick number
    rb            → round number
    fc            → face-up card index during dealing
    current_suit  → lead suit index
"""
from __future__ import annotations

import copy
import logging
from typing import Optional

from gbaloot.core.card_mapping import (
    decode_hand_bitmask,
    index_to_card,
    suit_idx_to_symbol,
    MODE_MAP,
    SUIT_SYMBOL_TO_IDX,
)

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────

POSITIONS = ("Bottom", "Right", "Top", "Left")

GSTG_TO_PHASE: dict[int, str] = {
    1: "BIDDING",
    2: "PLAYING",
    3: "PLAYING",  # Trick complete → still PLAYING for BotAgent
}

# Game mode: int → str (supplement MODE_MAP which is str→str)
GM_INT_MAP: dict[int, str] = {
    1: "SUN",
    2: "HOKUM",
}


def _card_to_dict(card) -> dict:
    """Convert a Card object to the dict shape BotAgent expects."""
    return {"suit": card.suit, "rank": card.rank}


# ── StateBuilder ─────────────────────────────────────────────────────

class StateBuilder:
    """Translates SFS2X events into a BotAgent-compatible game_state dict.

    Usage::

        sb = StateBuilder(my_username="player123")
        for event in decoded_events:
            sb.process_event(event)
        if sb.is_my_turn():
            decision = bot_agent.get_decision(sb.game_state, player_index=0)
    """

    def __init__(self, my_username: str):
        self.my_username = my_username
        self.my_seat: Optional[int] = None  # 0-indexed Source seat
        self.game_state = self._empty_state()
        self._player_names: list[str] = ["", "", "", ""]
        self._trick_history: list[dict] = []
        self._current_trick_cards: list[dict] = []
        self._bid_history: list[dict] = []
        self._round_scores: dict[str, int] = {"us": 0, "them": 0}

    # ── Empty State Template ─────────────────────────────────────

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
                {
                    "hand": [],
                    "position": pos,
                    "name": f"Player_{i}",
                    "team": "us" if i % 2 == 0 else "them",
                    "avatar": "bot_1",
                    "profile": None,
                    "difficulty": None,
                    "strategy": "heuristic",
                }
                for i, pos in enumerate(POSITIONS)
            ],
            "tableCards": [],
            "currentTurnIndex": 0,
            "dealerIndex": 0,
            "bid": {
                "type": None,
                "bidder": None,
                "doubled": False,
                "suit": None,
                "level": 1,
                "variant": None,
            },
            "teamScores": {"us": 0, "them": 0},
            "matchScores": {"us": 0, "them": 0},
            "floorCard": None,
            "currentRoundTricks": [],
            "bidHistory": [],
            "strictMode": True,
            "trickCount": 0,
            "doublingLevel": 1,
            "isLocked": False,
            "qaydState": {},
            "sawaState": {},
            "akkaState": None,
            "declarations": {},
        }

    # ── Main Event Router ────────────────────────────────────────

    def process_event(self, event: dict):
        """Process a single decoded GameEvent dict.

        The event dict has:
          timestamp, direction, action, fields, raw_size

        Routing uses the *command name* which can come from:
          1. event["action"] — already resolved (e.g. "game_state") from capture files
          2. fields.p.c — nested command field in live SFS2X ExtensionResponse
          3. last_action.action — embedded in game_state payloads
        """
        action = event.get("action", "")
        fields = event.get("fields", {})
        if not isinstance(fields, dict):
            return

        # Check for JoinRoom event (a=4) — contains pinfo with player names
        if fields.get("a") == 4:
            self._process_join_room(fields)

        # Extract the game payload (nested p→p structure)
        payload = self._extract_payload(fields)

        # Resolve command name: prefer fields.p.c over event["action"]
        # for live SFS2X where action is raw "sfs_cmd:C:A" format
        cmd = self._resolve_command(action, fields)

        # Identity discovery (from any event that has sn0..sn3 or pinfo)
        self._discover_identity(payload)

        # Route by resolved command name
        if cmd in ("game_state", "a_game_state_change", "card_or_play",
                    "sun_state", "hokum_state", "game_loaded"):
            self._process_game_state(payload)

        elif cmd in ("a_card_played", "card_play"):
            self._process_card_play(payload)

        elif cmd in ("a_cards_eating", "a_trick_end"):
            self._process_trick_won(payload)

        elif cmd in ("a_bid", "hokom"):
            self._process_bid(payload)

        elif cmd in ("hokom_result",):
            self._process_bid_end(payload)

        elif cmd in ("a_hand_dealt", "deal"):
            self._process_deal(payload)

        elif cmd in ("round_over", "game_stat", "round_result",
                      "a_round_end", "a_score_update"):
            self._process_round_end(payload)

    # ── JoinRoom Processing ─────────────────────────────────────

    def _process_join_room(self, fields: dict):
        """Extract player names from JoinRoom event (a=4).

        In live Kammelna, the JoinRoom response carries room variables
        including 'pinfo' which lists player names and IDs:

          fields.p.r[8] → list of room variables
          Each variable: [name, type, value, ...]
          pinfo value: [{n: "Name", i: id, pts: points, ...}, ...]

        Also extracts from the user list (ul) which has individual
        user variable arrays.
        """
        p = fields.get("p", {})
        if not isinstance(p, dict):
            return

        # Extract pinfo from room variables (fields.p.r[8])
        r = p.get("r")
        if isinstance(r, list) and len(r) > 8:
            room_vars = r[8]
            if isinstance(room_vars, list):
                for var in room_vars:
                    if isinstance(var, list) and len(var) > 2 and var[0] == "pinfo":
                        pinfo_data = var[2]
                        if isinstance(pinfo_data, list):
                            self._extract_pinfo_names(pinfo_data)

        # Extract from user list (fields.p.ul)
        ul = p.get("ul")
        if isinstance(ul, list):
            self._extract_user_list_names(ul)

    def _extract_pinfo_names(self, pinfo: list):
        """Extract player names from pinfo array [{n, i, pts, ...}, ...].

        Uses two passes: first collect all names, then set seat and remap.
        """
        found_seat = None
        # Pass 1: collect all names
        for seat_idx, info in enumerate(pinfo):
            if seat_idx >= 4:
                break
            if isinstance(info, dict):
                name = info.get("n", "")
                if name:
                    self._player_names[seat_idx] = str(name)
                    if str(name) == self.my_username and self.my_seat is None:
                        found_seat = seat_idx
        # Pass 2: set seat and remap (after all names are collected)
        if found_seat is not None and self.my_seat is None:
            self.my_seat = found_seat
            logger.info(f"Identity discovered from pinfo: seat {found_seat} ({self.my_username})")
            self._remap_player_names()

    def _extract_user_list_names(self, ul: list):
        """Extract player names from user list (ul) in JoinRoom.

        Each entry: [internal_id, user_id_str, ?, seat_1indexed, [[key, type, value, ...], ...]]
        Seat is the 4th element (1-indexed).
        Name is in the variable list where key == 'n'.

        Uses two passes: first collect all names, then set seat and remap.
        """
        found_seat = None
        # Pass 1: collect all names
        for entry in ul:
            if not isinstance(entry, list) or len(entry) < 5:
                continue
            try:
                seat_1indexed = entry[3]
                if not isinstance(seat_1indexed, (int, float)):
                    continue
                seat_0indexed = int(seat_1indexed) - 1
                if seat_0indexed < 0 or seat_0indexed > 3:
                    continue
                # Extract name from variable list
                var_list = entry[4]
                if isinstance(var_list, list):
                    for var in var_list:
                        if isinstance(var, list) and len(var) >= 3 and var[0] == "n":
                            name = str(var[2]) if var[2] else ""
                            if name:
                                self._player_names[seat_0indexed] = name
                                if name == self.my_username and self.my_seat is None:
                                    found_seat = seat_0indexed
            except (IndexError, TypeError, ValueError):
                continue
        # Pass 2: set seat and remap (after all names are collected)
        if found_seat is not None and self.my_seat is None:
            self.my_seat = found_seat
            logger.info(f"Identity discovered from ul: seat {found_seat} ({self.my_username})")
            self._remap_player_names()

    # ── Payload Extraction ───────────────────────────────────────

    @staticmethod
    @staticmethod
    def _resolve_command(action: str, fields: dict) -> str:
        """Resolve the SFS2X command name for event routing.

        In captured session files, the action is already resolved to the
        command name (e.g. "game_state"). In live SFS2X, the action string
        is raw "sfs_cmd:C:A" and the actual command is in fields.p.c.

        Falls back to last_action.action from the game_state payload.
        """
        # 1. Already a named command (from captured sessions)?
        if action and not action.startswith("sfs_cmd:"):
            return action

        # 2. Nested command field: fields.p.c (live SFS2X ExtensionResponse)
        p = fields.get("p")
        if isinstance(p, dict):
            c = p.get("c")
            if isinstance(c, str):
                return c

        # 3. Last resort: embedded last_action.action in the game payload
        if isinstance(p, dict):
            pp = p.get("p")
            if isinstance(pp, dict):
                la = pp.get("last_action")
                if isinstance(la, dict):
                    la_action = la.get("action")
                    if isinstance(la_action, str):
                        return la_action

        return action

    @staticmethod
    def _extract_payload(fields: dict) -> dict:
        """Walk the fields.p.p nesting to find the inner game payload."""
        payload = fields
        p = fields.get("p")
        if isinstance(p, dict):
            payload = p
            pp = p.get("p")
            if isinstance(pp, dict):
                payload = pp
        return payload

    # ── Identity Discovery ───────────────────────────────────────

    def _discover_identity(self, payload: dict):
        """Find which seat we occupy by matching username to sn0..sn3 or pinfo[].n.

        Live Kammelna uses TWO player-name formats:
          1. sn0..sn3 — flat fields, one per seat (original format)
          2. pinfo — array of {n: name, i: id, ...} dicts, indexed by seat
        """
        if self.my_seat is not None:
            return  # Already discovered

        found_seat = None

        # Format 1: sn0..sn3 flat fields
        for i in range(4):
            name = payload.get(f"sn{i}")
            if name is not None:
                self._player_names[i] = str(name)
                if str(name) == self.my_username:
                    found_seat = i

        # Format 2: pinfo array [{n: "name", i: id, ...}, ...]
        pinfo = payload.get("pinfo")
        if isinstance(pinfo, list):
            for i, info in enumerate(pinfo):
                if i >= 4:
                    break
                if isinstance(info, dict):
                    name = info.get("n", "")
                    if name:
                        self._player_names[i] = str(name)
                        if str(name) == self.my_username:
                            found_seat = i

        # If we found our seat, set it and remap
        if found_seat is not None:
            self.my_seat = found_seat
            logger.info(f"Identity discovered: we are seat {found_seat} ({self.my_username})")
            self._remap_player_names()

    def _remap_player_names(self):
        """Once our seat is known, assign names to the remapped positions."""
        if self.my_seat is None:
            return
        for src_seat in range(4):
            our_idx = self._remap_seat(src_seat)
            name = self._player_names[src_seat]
            if name:
                self.game_state["players"][our_idx]["name"] = name

    # ── Seat Remapping ───────────────────────────────────────────

    def _remap_seat(self, source_seat_0indexed: int) -> int:
        """Convert Source 0-indexed seat to our perspective.

        If we are seat 2 in Source:
          Source 2 → Our 0 (Bottom, us)
          Source 3 → Our 1 (Right)
          Source 0 → Our 2 (Top, partner)
          Source 1 → Our 3 (Left)
        """
        if self.my_seat is None:
            return source_seat_0indexed
        return (source_seat_0indexed - self.my_seat) % 4

    def _source_seat_from_1indexed(self, seat_1indexed) -> int:
        """Convert a Source 1-indexed seat to 0-indexed."""
        if seat_1indexed is None or not isinstance(seat_1indexed, (int, float)):
            return 0
        return int(seat_1indexed) - 1

    # ── Game State Processing (the main translator) ──────────────

    def _process_game_state(self, payload: dict):
        """Translate SFS2X game_state payload → BotAgent game_state dict."""
        # Phase
        gStg = payload.get("gStg")
        if gStg is not None:
            self.game_state["phase"] = GSTG_TO_PHASE.get(int(gStg), "PLAYING")

        # Game mode (can be int or string)
        gm = payload.get("gm")
        if gm is not None:
            if isinstance(gm, int):
                self.game_state["gameMode"] = GM_INT_MAP.get(gm, "SUN")
            elif isinstance(gm, str):
                mapped = MODE_MAP.get(gm.lower())
                if mapped:
                    self.game_state["gameMode"] = mapped

        # Trump suit (HOKUM only)
        ts = payload.get("ts")
        if ts is not None and isinstance(ts, (int, float)):
            if self.game_state["gameMode"] == "HOKUM":
                symbol = suit_idx_to_symbol(int(ts))
                self.game_state["trumpSuit"] = symbol
                self.game_state["bid"]["suit"] = symbol
        if self.game_state["gameMode"] == "SUN":
            self.game_state["trumpSuit"] = None

        # Dealer (1-indexed → 0-indexed → remapped)
        dealer = payload.get("dealer")
        if dealer is not None:
            src_seat = self._source_seat_from_1indexed(dealer)
            self.game_state["dealerIndex"] = self._remap_seat(src_seat)

        # Mover / current turn (1-indexed → 0-indexed → remapped)
        mover = payload.get("mover")
        if mover is not None:
            src_seat = self._source_seat_from_1indexed(mover)
            self.game_state["currentTurnIndex"] = self._remap_seat(src_seat)

        # Player hand (bitmask)
        pcs = payload.get("pcs")
        if pcs is not None:
            if isinstance(pcs, (int, float)):
                # Single bitmask — only our hand
                cards = decode_hand_bitmask(int(pcs))
                hand = [_card_to_dict(c) for c in cards]
                # Assign to our seat (index 0 after remap)
                self.game_state["players"][0]["hand"] = hand
            elif isinstance(pcs, list) and len(pcs) == 4:
                # Array of bitmasks — one per Source seat
                for src_seat in range(4):
                    our_idx = self._remap_seat(src_seat)
                    bitmask = pcs[src_seat]
                    if isinstance(bitmask, (int, float)) and int(bitmask) > 0:
                        cards = decode_hand_bitmask(int(bitmask))
                        hand = [_card_to_dict(c) for c in cards]
                        self.game_state["players"][our_idx]["hand"] = hand

        # Table cards (played_cards array)
        played = payload.get("played_cards")
        if isinstance(played, list) and len(played) == 4:
            table: list[dict] = []
            for src_seat in range(4):
                card_idx = played[src_seat]
                if isinstance(card_idx, (int, float)) and int(card_idx) >= 0:
                    card = index_to_card(int(card_idx))
                    if card is not None:
                        our_idx = self._remap_seat(src_seat)
                        table.append({
                            "card": _card_to_dict(card),
                            "playedBy": POSITIONS[our_idx],
                            "playerId": None,
                            "metadata": None,
                        })
            self.game_state["tableCards"] = table

        # Scores (ss is 4-element array: [seat0, seat1, seat2, seat3])
        ss = payload.get("ss")
        if isinstance(ss, list) and len(ss) == 4:
            # Teams: seats 0,2 vs seats 1,3 (in Source indexing)
            # After remap: us = indices 0,2, them = indices 1,3
            if self.my_seat is not None:
                us_seats = [self.my_seat, (self.my_seat + 2) % 4]
                them_seats = [(self.my_seat + 1) % 4, (self.my_seat + 3) % 4]
            else:
                us_seats = [0, 2]
                them_seats = [1, 3]
            our_score = sum(ss[s] for s in us_seats if isinstance(ss[s], (int, float)))
            their_score = sum(ss[s] for s in them_seats if isinstance(ss[s], (int, float)))
            self.game_state["teamScores"] = {"us": our_score, "them": their_score}

        # Trick number
        mn = payload.get("mn")
        if mn is not None and isinstance(mn, (int, float)):
            self.game_state["trickCount"] = int(mn)

        # Round number
        rb = payload.get("rb")
        if rb is not None and isinstance(rb, (int, float)):
            self.game_state["biddingRound"] = int(rb)

        # Floor card (shown during bidding)
        fc = payload.get("fc")
        if fc is not None and isinstance(fc, (int, float)) and int(fc) >= 0:
            card = index_to_card(int(fc))
            if card is not None:
                self.game_state["floorCard"] = _card_to_dict(card)

        # Detect new round (pcsCount reset to 8)
        pcsCount = payload.get("pcsCount")
        if isinstance(pcsCount, list) and len(pcsCount) == 4:
            if all(isinstance(c, (int, float)) and int(c) == 8 for c in pcsCount):
                self._start_new_round()

        # Declarations (dp field: [[], ["baloot"], [], []])
        dp = payload.get("dp")
        if isinstance(dp, list) and len(dp) == 4:
            decl = {}
            for src_seat in range(4):
                our_idx = self._remap_seat(src_seat)
                pos = POSITIONS[our_idx]
                seat_decl = dp[src_seat]
                if isinstance(seat_decl, list) and seat_decl:
                    decl[pos] = seat_decl
            if decl:
                self.game_state["declarations"] = decl

        # Player identity from pinfo (live Kammelna format)
        pinfo = payload.get("pinfo")
        if isinstance(pinfo, list):
            for src_seat, info in enumerate(pinfo):
                if src_seat >= 4 or not isinstance(info, dict):
                    continue
                our_idx = self._remap_seat(src_seat)
                name = info.get("n", "")
                if name:
                    self.game_state["players"][our_idx]["name"] = str(name)

        # Bidding from last_action
        last_action = payload.get("last_action")
        if isinstance(last_action, dict):
            self._process_last_action(last_action)

    # ── Card Play Processing ─────────────────────────────────────

    def _process_card_play(self, payload: dict):
        """Handle a card-played event."""
        # The payload might have the card info in various forms
        # Often arrives via game_state update with played_cards populated
        # We rely on _process_game_state for table card updates
        pass

    # ── Trick Won Processing ─────────────────────────────────────

    def _process_trick_won(self, payload: dict):
        """Handle trick completion — archive table cards to trick history."""
        if not self.game_state["tableCards"]:
            return

        # Determine winner from payload (ap = 1-indexed winner seat)
        winner_pos = "Bottom"
        ap = payload.get("ap")
        if ap is not None and isinstance(ap, (int, float)):
            src_seat = int(ap) - 1
            our_idx = self._remap_seat(src_seat)
            winner_pos = POSITIONS[our_idx]

        # Archive the trick
        trick = {
            "winner": winner_pos,
            "points": 0,
            "cards": copy.deepcopy(self.game_state["tableCards"]),
        }
        self.game_state["currentRoundTricks"].append(trick)
        self.game_state["trickCount"] = len(self.game_state["currentRoundTricks"])

        # Clear table
        self.game_state["tableCards"] = []

    # ── Bidding Processing ───────────────────────────────────────

    def _process_bid(self, payload: dict):
        """Handle a bid action event."""
        bt = payload.get("bt", payload.get("bid", ""))
        ap = payload.get("ap")

        if ap is not None:
            src_seat = self._source_seat_from_1indexed(ap)
            our_idx = self._remap_seat(src_seat)
            bidder_pos = POSITIONS[our_idx]
        else:
            bidder_pos = "Bottom"

        # Determine action type
        action = "PASS"
        suit = None
        if isinstance(bt, str):
            bt_lower = bt.lower()
            if bt_lower in ("sun", "ashkal"):
                action = "SUN"
            elif bt_lower in ("hokom", "hokum"):
                action = "HOKUM"
                # Trump suit from ts field
                ts = payload.get("ts")
                if ts is not None and isinstance(ts, (int, float)):
                    suit = suit_idx_to_symbol(int(ts))
            elif bt_lower == "pass":
                action = "PASS"
        elif isinstance(bt, int):
            if bt == 1:
                action = "SUN"
            elif bt == 2:
                action = "HOKUM"
                ts = payload.get("ts")
                if ts is not None and isinstance(ts, (int, float)):
                    suit = suit_idx_to_symbol(int(ts))
            else:
                action = "PASS"

        bid_entry = {"player": bidder_pos, "action": action, "suit": suit}
        self.game_state["bidHistory"].append(bid_entry)

        # Update bid state if it's a real bid (not PASS)
        if action != "PASS":
            self.game_state["bid"]["type"] = action
            self.game_state["bid"]["bidder"] = bidder_pos
            if suit:
                self.game_state["bid"]["suit"] = suit

    def _process_bid_end(self, payload: dict):
        """Handle bid resolution — set final game mode and trump."""
        gm = payload.get("gm")
        if gm is not None:
            if isinstance(gm, int):
                self.game_state["gameMode"] = GM_INT_MAP.get(gm, "SUN")
            elif isinstance(gm, str):
                mapped = MODE_MAP.get(gm.lower())
                if mapped:
                    self.game_state["gameMode"] = mapped

        ts = payload.get("ts")
        if ts is not None and isinstance(ts, (int, float)):
            if self.game_state["gameMode"] == "HOKUM":
                self.game_state["trumpSuit"] = suit_idx_to_symbol(int(ts))

        self.game_state["phase"] = "PLAYING"

    def _process_last_action(self, last_action: dict):
        """Extract bidding/play info from the last_action sub-dict."""
        la_action = last_action.get("action", "")
        la_ap = last_action.get("ap")
        la_bt = last_action.get("bt")

        if la_action == "a_bid" and la_bt is not None:
            # Process as a bid
            self._process_bid({"bt": la_bt, "ap": la_ap, "ts": last_action.get("ts")})

    # ── Deal Processing ──────────────────────────────────────────

    def _process_deal(self, payload: dict):
        """Handle a new deal — reset round state."""
        self._start_new_round()

    def _start_new_round(self):
        """Reset per-round state for a new round."""
        self.game_state["currentRoundTricks"] = []
        self.game_state["tableCards"] = []
        self.game_state["bidHistory"] = []
        self.game_state["trickCount"] = 0
        self.game_state["floorCard"] = None
        self.game_state["bid"] = {
            "type": None,
            "bidder": None,
            "doubled": False,
            "suit": None,
            "level": 1,
            "variant": None,
        }

    # ── Round End Processing ─────────────────────────────────────

    def _process_round_end(self, payload: dict):
        """Handle round completion."""
        self.game_state["phase"] = "FINISHED"

        # Update match scores if available
        # Match score fields vary; try common patterns
        for key in ("matchScore", "totalScore", "ms"):
            val = payload.get(key)
            if isinstance(val, list) and len(val) >= 2:
                if self.my_seat is not None:
                    # Team scoring: our team vs their team
                    our_team = self.my_seat % 2  # 0 or 1
                    their_team = 1 - our_team
                    if our_team < len(val) and their_team < len(val):
                        self.game_state["matchScores"]["us"] = val[our_team]
                        self.game_state["matchScores"]["them"] = val[their_team]

    # ── Turn Detection ───────────────────────────────────────────

    def is_my_turn(self) -> bool:
        """Check if it's our turn to act."""
        phase = self.game_state.get("phase")
        if phase not in ("BIDDING", "PLAYING", "DOUBLING"):
            return False
        if self.my_seat is None:
            return False
        # We are always index 0 after remapping
        return self.game_state["currentTurnIndex"] == 0

    # ── Snapshot ─────────────────────────────────────────────────

    def get_snapshot(self) -> dict:
        """Return a deep copy of the current game state."""
        return copy.deepcopy(self.game_state)

    # ── Debug ────────────────────────────────────────────────────

    def summary(self) -> str:
        """Return a human-readable summary of the current state."""
        gs = self.game_state
        hand = gs["players"][0]["hand"] if gs["players"] else []
        hand_str = ", ".join(f"{c['rank']}{c['suit']}" for c in hand)
        table_str = ", ".join(
            f"{tc['card']['rank']}{tc['card']['suit']}({tc['playedBy']})"
            for tc in gs.get("tableCards", [])
        )
        return (
            f"Phase={gs['phase']} Mode={gs['gameMode']} Trump={gs['trumpSuit']} "
            f"Turn={gs['currentTurnIndex']} MyTurn={self.is_my_turn()} "
            f"Hand=[{hand_str}] Table=[{table_str}] "
            f"Score={gs['teamScores']} Tricks={gs['trickCount']}"
        )
