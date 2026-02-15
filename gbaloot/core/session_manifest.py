"""
Session Manifest — Shared health index for all processed sessions.

Scans the sessions directory once and builds a manifest with per-session
metadata (trick count, bid presence, round count, agreement percentage,
health classification).  All UI sections can read the cached manifest
instead of independently re-scanning the filesystem.

Usage::

    manifest = build_manifest(sessions_dir)
    save_manifest(manifest, sessions_dir)
    manifest = load_manifest(sessions_dir)
    healthy = get_sessions_by_health(manifest, "good")
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "session_manifest.json"


# ── Data Model ────────────────────────────────────────────────────────

@dataclass
class SessionEntry:
    """Health summary for a single processed session.

    @param filename: Name of the processed JSON file (e.g. ``capture_v3_processed.json``).
    @param label: Human-readable session label from capture metadata.
    @param has_tricks: Whether the session contains extractable trick data.
    @param trick_count: Number of complete tricks extracted.
    @param has_bids: Whether bidding events were detected.
    @param round_count: Number of game rounds detected.
    @param agreement_pct: Engine agreement percentage (0-100), or None if not compared.
    @param event_count: Total number of decoded events.
    @param game_event_count: Number of game-related events (game_state, card_or_play).
    @param health: Classification — ``'good'``, ``'partial'``, ``'empty'``.
    """
    filename: str
    label: str = ""
    has_tricks: bool = False
    trick_count: int = 0
    has_bids: bool = False
    round_count: int = 0
    agreement_pct: Optional[float] = None
    event_count: int = 0
    game_event_count: int = 0
    health: str = "empty"  # good / partial / empty

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Manifest:
    """Collection of all session entries with aggregate stats.

    @param entries: List of SessionEntry objects.
    @param total_sessions: Total number of sessions scanned.
    @param good_count: Sessions classified as ``'good'``.
    @param partial_count: Sessions classified as ``'partial'``.
    @param empty_count: Sessions classified as ``'empty'``.
    """
    entries: list[SessionEntry] = field(default_factory=list)
    total_sessions: int = 0
    good_count: int = 0
    partial_count: int = 0
    empty_count: int = 0

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total_sessions": self.total_sessions,
            "good_count": self.good_count,
            "partial_count": self.partial_count,
            "empty_count": self.empty_count,
        }


# ── Health Classification ─────────────────────────────────────────────

def classify_health(entry: SessionEntry) -> str:
    """Determine session health based on extracted data.

    - ``'good'``: has tricks and at least one complete round.
    - ``'partial'``: has some game events but no complete tricks.
    - ``'empty'``: no game events at all.

    @param entry: SessionEntry with populated fields.
    @returns Health string.
    """
    if entry.has_tricks and entry.trick_count > 0:
        return "good"
    if entry.game_event_count > 0:
        return "partial"
    return "empty"


HEALTH_ICONS: dict[str, str] = {
    "good": "🟢",
    "partial": "🟡",
    "empty": "🔴",
}


# ── Build Manifest ────────────────────────────────────────────────────

GAME_STATE_ACTIONS = frozenset({"game_state", "card_or_play"})
BID_ACTIONS = frozenset({"a_bid", "u_bid", "hokom", "sira"})


def _analyze_session_file(path: Path) -> SessionEntry:
    """Analyze a single processed session JSON and produce a SessionEntry.

    @param path: Path to a ``*_processed.json`` file.
    @returns Populated SessionEntry.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read %s: %s", path.name, exc)
        return SessionEntry(filename=path.name, health="empty")

    label = data.get("label", "")
    events = data.get("events", [])
    event_count = len(events)

    # Count game events and detect bid actions
    game_event_count = 0
    has_bids = False
    round_numbers: set[int] = set()
    trick_count = 0

    for ev in events:
        action = ev.get("action", "")
        if action in GAME_STATE_ACTIONS:
            game_event_count += 1

            # Inspect inner payload for trick and round data
            inner = _get_inner(ev)
            if inner:
                rb = inner.get("rb")
                if isinstance(rb, (int, float)) and rb > 0:
                    round_numbers.add(int(rb))

                played = inner.get("played_cards")
                if isinstance(played, list) and len(played) == 4:
                    if all(isinstance(c, (int, float)) and int(c) >= 0 for c in played):
                        trick_count += 1

                la = inner.get("last_action")
                if isinstance(la, dict) and la.get("action") in ("a_bid",):
                    has_bids = True

        elif action in BID_ACTIONS:
            has_bids = True

    has_tricks = trick_count > 0
    round_count = len(round_numbers)

    entry = SessionEntry(
        filename=path.name,
        label=label,
        has_tricks=has_tricks,
        trick_count=trick_count,
        has_bids=has_bids,
        round_count=round_count,
        event_count=event_count,
        game_event_count=game_event_count,
    )
    entry.health = classify_health(entry)
    return entry


def _get_inner(event: dict) -> Optional[dict]:
    """Extract the inner game state dict from fields.p.p, if present."""
    fields = event.get("fields", {})
    if not isinstance(fields, dict):
        return None
    p = fields.get("p")
    if not isinstance(p, dict):
        return None
    inner = p.get("p")
    if isinstance(inner, dict):
        return inner
    return None


def build_manifest(sessions_dir: Path) -> Manifest:
    """Scan a sessions directory and build a fresh manifest.

    @param sessions_dir: Directory containing ``*_processed.json`` files.
    @returns Manifest with entries for every session found.
    """
    if not sessions_dir.exists():
        return Manifest()

    files = sorted(sessions_dir.glob("*_processed.json"))
    entries: list[SessionEntry] = []

    for path in files:
        entry = _analyze_session_file(path)
        entries.append(entry)

    good = sum(1 for e in entries if e.health == "good")
    partial = sum(1 for e in entries if e.health == "partial")
    empty = sum(1 for e in entries if e.health == "empty")

    return Manifest(
        entries=entries,
        total_sessions=len(entries),
        good_count=good,
        partial_count=partial,
        empty_count=empty,
    )


# ── Persistence ───────────────────────────────────────────────────────

def save_manifest(manifest: Manifest, sessions_dir: Path) -> Path:
    """Save manifest to JSON in the sessions directory.

    @param manifest: Manifest to save.
    @param sessions_dir: Directory to write ``session_manifest.json`` into.
    @returns Path to the saved file.
    """
    sessions_dir.mkdir(parents=True, exist_ok=True)
    out = sessions_dir / MANIFEST_FILENAME
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
    return out


def load_manifest(sessions_dir: Path) -> Optional[Manifest]:
    """Load a previously saved manifest, or return None if not found.

    @param sessions_dir: Directory containing ``session_manifest.json``.
    @returns Manifest object, or None.
    """
    path = sessions_dir / MANIFEST_FILENAME
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    entries = [
        SessionEntry(**e)
        for e in data.get("entries", [])
    ]
    return Manifest(
        entries=entries,
        total_sessions=data.get("total_sessions", len(entries)),
        good_count=data.get("good_count", 0),
        partial_count=data.get("partial_count", 0),
        empty_count=data.get("empty_count", 0),
    )


# ── Filtering ─────────────────────────────────────────────────────────

def get_sessions_by_health(
    manifest: Manifest, health: str
) -> list[SessionEntry]:
    """Filter manifest entries by health classification.

    @param manifest: Manifest to filter.
    @param health: One of ``'good'``, ``'partial'``, ``'empty'``.
    @returns List of matching SessionEntry objects.
    """
    return [e for e in manifest.entries if e.health == health]


def get_entry_by_filename(
    manifest: Manifest, filename: str
) -> Optional[SessionEntry]:
    """Find a specific session entry by filename.

    @param manifest: Manifest to search.
    @param filename: Exact filename to match.
    @returns SessionEntry, or None if not found.
    """
    for e in manifest.entries:
        if e.filename == filename:
            return e
    return None
