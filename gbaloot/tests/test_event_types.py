"""
Tests for event_types — canonical action classification.
"""
import pytest
from gbaloot.core.event_types import (
    GAME_EVENT_CATEGORIES,
    ALL_GAME_ACTIONS,
    SCREENSHOT_TRIGGERS,
)


class TestGameEventCategories:
    def test_all_categories_present(self):
        expected = {
            "bid_phase", "card_played", "trick_won", "round_over",
            "game_state", "connection", "player", "chat",
            "game_control", "special_actions",
        }
        assert set(GAME_EVENT_CATEGORIES.keys()) == expected

    def test_all_categories_have_keywords(self):
        for cat, keywords in GAME_EVENT_CATEGORIES.items():
            assert len(keywords) > 0, f"Category {cat} has no keywords"

    def test_no_cross_category_duplicates(self):
        """No keyword should appear in multiple categories."""
        seen: dict[str, str] = {}
        for cat, keywords in GAME_EVENT_CATEGORIES.items():
            for kw in keywords:
                assert kw not in seen, f"'{kw}' duplicated in {cat} and {seen[kw]}"
                seen[kw] = cat


class TestAllGameActions:
    def test_is_superset_of_all_categories(self):
        for cat, keywords in GAME_EVENT_CATEGORIES.items():
            for kw in keywords:
                assert kw in ALL_GAME_ACTIONS, f"'{kw}' from {cat} missing in ALL_GAME_ACTIONS"

    def test_count_matches(self):
        total = sum(len(kws) for kws in GAME_EVENT_CATEGORIES.values())
        assert len(ALL_GAME_ACTIONS) == total


class TestScreenshotTriggers:
    def test_triggers_are_subset_of_all_actions(self):
        assert SCREENSHOT_TRIGGERS.issubset(ALL_GAME_ACTIONS)

    def test_key_triggers_present(self):
        for trigger in ["a_bid", "a_card_played", "a_cards_eating", "game_state"]:
            assert trigger in SCREENSHOT_TRIGGERS

    def test_special_triggers_present(self):
        for trigger in ["a_kaboot_call", "a_galoss", "a_sawa_claim"]:
            assert trigger in SCREENSHOT_TRIGGERS


class TestSpecialActions:
    def test_kaboot_present(self):
        assert "a_kaboot_call" in ALL_GAME_ACTIONS

    def test_sawa_present(self):
        assert "a_sawa_claim" in ALL_GAME_ACTIONS

    def test_galoss_present(self):
        assert "a_galoss" in ALL_GAME_ACTIONS

    def test_baloot_claim_present(self):
        assert "a_baloot_claim" in ALL_GAME_ACTIONS

    def test_qayd_family_present(self):
        for action in ["a_qayd", "a_qayd_accept", "a_qayd_reject"]:
            assert action in ALL_GAME_ACTIONS
