"""
tests/game_logic/__init__.py — Compatibility shim for legacy test imports.

All tests import from `game_logic` but the actual code now lives in `game_engine.*`.
This module re-exports everything tests need so `from game_logic import Game` works.
"""

# Core classes
from game_engine.logic.game import Game
from game_engine.models.player import Player
from game_engine.models.card import Card

# Constants & Enums
from game_engine.models.constants import (
    GamePhase,
    BiddingPhase,
    BidType,
    SUITS,
    RANKS,
    ORDER_SUN,
    ORDER_HOKUM,
    ORDER_PROJECTS,
    POINT_VALUES_SUN,
    POINT_VALUES_HOKUM,
)

# Utils (project logic)
from game_engine.logic.utils import (
    scan_hand_for_projects,
    compare_projects,
    sort_hand,
    is_kawesh_hand,
)

# Legacy alias: validate_project was renamed to check_project_eligibility
from game_engine.logic.rules.projects import check_project_eligibility as validate_project
