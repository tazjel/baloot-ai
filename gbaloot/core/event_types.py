"""
GBaloot Event Types — Single source of truth for game action classification.

R5: Unifies event keywords from capture_session.py, capturer.py, and decoder.py
into one canonical module. All three files import from here.

Categories:
    bid_phase    — Bidding actions
    card_played  — Card play events
    trick_won    — Trick resolution
    round_over   — Round/game completion
    game_state   — State snapshots
    connection   — Connection lifecycle
    player       — Player join/leave
    chat         — Non-game communication
"""


# ── Categorized Game Actions ──────────────────────────────────────
# Each category maps to a list of action keywords recognized in the
# SFS2X protocol. Keywords should be specific enough to avoid false
# positives when matched with delimiter-aware regex.

GAME_EVENT_CATEGORIES: dict[str, list[str]] = {
    "bid_phase": [
        "a_bid", "hokom", "hokom_result", "pass", "sira",
    ],
    "card_played": [
        "a_card_played", "card_play",
    ],
    "trick_won": [
        "a_cards_eating", "a_trick_end",
    ],
    "round_over": [
        "round_over", "game_stat", "round_result",
        "a_round_end", "a_score_update",
    ],
    "game_state": [
        "game_state", "sun_state", "hokum_state",
        "game_loaded", "a_hand_dealt",
    ],
    "connection": [
        "CONNECT", "CLOSE", "login", "join_room",
        "a_disconnect", "a_reconnect", "a_timeout",
    ],
    "player": [
        "a_player_joined", "a_player_left", "a_kick",
        "a_leave", "switch_seat", "find_match",
    ],
    "chat": [
        "chat", "a_emoji", "a_sticker",
    ],
    "game_control": [
        "a_accept_next_move", "a_back", "a_draw",
        "a_new_game", "a_rematch",
    ],
    "special_actions": [
        "a_kaboot_call", "a_sawa_claim", "a_galoss",
        "a_baloot_claim", "a_qayd", "a_qayd_accept", "a_qayd_reject",
    ],
}


# ── Flat set of ALL known game actions ────────────────────────────
# Used by decoder.py for action classification.
ALL_GAME_ACTIONS: set[str] = set()
for _keywords in GAME_EVENT_CATEGORIES.values():
    ALL_GAME_ACTIONS.update(_keywords)


# ── Screenshot triggers ──────────────────────────────────────────
# Subset of actions that should trigger an event-based screenshot
# during live capture. Excludes high-frequency events like game_state.
SCREENSHOT_TRIGGERS: set[str] = {
    "a_bid", "hokom", "pass",           # Bidding phase
    "a_card_played",                     # Card played
    "a_cards_eating",                    # Trick won
    "game_stat", "round_over",          # Round / game over
    "game_state",                        # State changes
    "a_kaboot_call", "a_galoss",        # Special actions
    "a_sawa_claim", "a_baloot_claim",   # Declarations
}
