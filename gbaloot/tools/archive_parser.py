"""
Archive Parser -- Load and validate source platform mobile archive JSON files.

Mobile archives are complete game replays captured from the source platform Android
app.  Each JSON file contains every bid, card play, trick winner, and round
result for an entire game session.

The parser validates structure, extracts metadata, and provides a clean
``ArchiveGame`` dataclass for downstream consumers.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────

# Event type codes in the mobile archive format
EVT_HAND_DEALT = 15
EVT_ROUND_START = 1
EVT_BID = 2
EVT_DECLARATION = 3
EVT_CARD_PLAYED = 4
EVT_KABOOT = 5
EVT_TRICK_WON = 6
EVT_CHALLENGE = 7     # Qayd/challenge event
EVT_CHAT = 8
EVT_DB_REF = 10       # Database reference
EVT_ROUND_RESULT = 12
EVT_EMOJI = 16        # Emoji reaction

# Archive trump suit encoding -> our card_mapping suit index
# Archive: 1=spade, 2=clubs, 3=diamonds, 4=hearts
# card_mapping: 0=spade, 1=hearts, 2=clubs, 3=diamonds
ARCHIVE_TS_TO_SUIT_IDX: dict[int, int] = {
    1: 0,   # spade  -> 0
    2: 2,   # clubs  -> 2
    3: 3,   # diamonds -> 3
    4: 1,   # hearts -> 1
}

# Archive game mode encoding -> our mode strings
# gm=1: SUN, gm=2: HOKUM, gm=3: Ashkal (variant of SUN)
ARCHIVE_GM_TO_MODE: dict[int, str] = {
    1: "SUN",
    2: "HOKUM",
    3: "SUN",  # Ashkal = SUN mode
}


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class ArchiveRound:
    """One round parsed from the mobile archive.

    @param round_index: 0-based round number within the game.
    @param events: Raw event dicts from the archive ``r`` array.
    @param game_mode: 'SUN' or 'HOKUM' (resolved from bidding).
    @param trump_suit_idx: Our card_mapping suit index; None for SUN.
    @param bidder_seat: 0-indexed seat of the contract winner (-1 if unknown).
    @param result: Raw round result dict (from e=12), or None.
    """
    round_index: int
    events: list[dict]
    game_mode: Optional[str] = None
    trump_suit_idx: Optional[int] = None
    bidder_seat: int = -1
    result: Optional[dict] = None


@dataclass
class ArchiveGame:
    """Complete parsed game from a mobile archive file.

    @param file_path: Path to the source JSON file.
    @param version: Format version (``v`` field).
    @param session_name: Arabic session name (``n`` field).
    @param session_id: Game/session ID.
    @param player_names: Display names for seats 1-4 (1-indexed).
    @param player_ids: User IDs for seats 1-4 (1-indexed).
    @param final_score_team1: Final score for Team 1 (seats 1,3).
    @param final_score_team2: Final score for Team 2 (seats 2,4).
    @param rounds: Parsed rounds with metadata.
    @param warnings: Non-fatal issues encountered during parsing.
    """
    file_path: str
    version: int = 1
    session_name: str = ""
    session_id: int = 0
    player_names: list[str] = field(default_factory=list)
    player_ids: list[int] = field(default_factory=list)
    final_score_team1: int = 0
    final_score_team2: int = 0
    rounds: list[ArchiveRound] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Main Parsing Function ────────────────────────────────────────────

def parse_archive(archive_path: Path) -> ArchiveGame:
    """Parse a source platform mobile archive JSON file.

    Loads the JSON, validates required fields, extracts game metadata,
    and resolves bidding outcomes (game mode, trump suit) for each round.

    @param archive_path: Path to a ``*.json`` archive file.
    @returns ArchiveGame with all rounds and metadata.
    @raises FileNotFoundError: If the file does not exist.
    @raises json.JSONDecodeError: If the file is not valid JSON.
    @raises ValueError: If critical structure is missing.
    """
    with open(archive_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate top-level structure
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")
    if "rs" not in data:
        raise ValueError("Missing 'rs' (rounds) array in archive")

    game = ArchiveGame(
        file_path=str(archive_path),
        version=data.get("v", 1),
        session_name=data.get("n", ""),
        session_id=data.get("Id", 0),
        player_names=data.get("psN", []),
        player_ids=data.get("ps", []),
        final_score_team1=data.get("s1", 0),
        final_score_team2=data.get("s2", 0),
    )

    raw_rounds = data.get("rs", [])
    if not isinstance(raw_rounds, list):
        raise ValueError(f"'rs' must be a list, got {type(raw_rounds).__name__}")

    for ri, raw_round in enumerate(raw_rounds):
        events = raw_round.get("r", [])
        if not isinstance(events, list):
            game.warnings.append(f"Round {ri}: 'r' is not a list, skipping")
            continue

        # Resolve bidding for this round
        mode, trump_idx, bidder = _resolve_bidding(events, ri, game.warnings)

        # Extract round result
        result = _extract_round_result(events)

        game.rounds.append(ArchiveRound(
            round_index=ri,
            events=events,
            game_mode=mode,
            trump_suit_idx=trump_idx,
            bidder_seat=bidder,
            result=result,
        ))

    return game


def load_all_archives(directory: Path) -> list[ArchiveGame]:
    """Load all archive JSON files from a directory.

    @param directory: Path to the savedGames directory.
    @returns List of parsed ArchiveGame objects.
    """
    games: list[ArchiveGame] = []
    files = sorted(directory.glob("*.json"))

    for f in files:
        try:
            game = parse_archive(f)
            games.append(game)
        except Exception as e:
            logger.warning("Failed to parse %s: %s", f.name, e)

    return games


# ── Internal Helpers ─────────────────────────────────────────────────

def _resolve_bidding(
    events: list[dict],
    round_index: int,
    warnings: list[str],
) -> tuple[Optional[str], Optional[int], int]:
    """Walk bid events (e=2) and resolve game mode, trump suit, bidder.

    The contract is determined by the LAST bid event that sets ``gm``.
    The final ``ts`` on that settled bid gives the trump suit for HOKUM.

    @param events: Raw event list for one round.
    @param round_index: For warning messages.
    @param warnings: Accumulator for non-fatal issues.
    @returns (game_mode, trump_suit_idx, bidder_seat_0indexed).
    """
    game_mode: Optional[str] = None
    trump_suit_idx: Optional[int] = None
    bidder_seat: int = -1

    # Track the last bid that established the contract
    last_gm: Optional[int] = None
    last_ts: Optional[int] = None
    last_rb: int = -1

    for evt in events:
        if evt.get("e") != EVT_BID:
            continue

        gm = evt.get("gm")
        ts = evt.get("ts")
        rb = evt.get("rb", -1)
        bid_action = evt.get("b", "")

        # A bid that sets gm establishes or changes the contract
        if gm is not None:
            last_gm = gm
        if ts is not None:
            last_ts = ts
        if rb is not None and rb > 0:
            last_rb = rb

    # Resolve game mode
    if last_gm is not None:
        game_mode = ARCHIVE_GM_TO_MODE.get(last_gm)
        if game_mode is None:
            warnings.append(f"Round {round_index}: unknown gm={last_gm}")
    else:
        warnings.append(f"Round {round_index}: no gm found in bid events")

    # Resolve trump suit (only for HOKUM)
    if game_mode == "HOKUM" and last_ts is not None:
        trump_suit_idx = ARCHIVE_TS_TO_SUIT_IDX.get(last_ts)
        if trump_suit_idx is None:
            warnings.append(
                f"Round {round_index}: unknown trump ts={last_ts}"
            )

    # Bidder seat (convert 1-indexed to 0-indexed)
    if last_rb > 0:
        bidder_seat = last_rb - 1

    return game_mode, trump_suit_idx, bidder_seat


def _extract_round_result(events: list[dict]) -> Optional[dict]:
    """Find and return the round result event (e=12) if present.

    @param events: Raw event list for one round.
    @returns The ``rs`` dict from the result event, or None.
    """
    for evt in events:
        if evt.get("e") == EVT_ROUND_RESULT:
            return evt.get("rs")
    return None
