"""
Tests for Source card index mapping (gbaloot.core.card_mapping).

Covers: index↔Card round-trips, invalid index rejection, suit/rank symbols,
decode_hand_bitmask, map_game_mode, card_code_to_card, and edge cases.
"""
import pytest

from game_engine.models.card import Card
from gbaloot.core.card_mapping import (
    index_to_card,
    card_to_index,
    suit_idx_to_symbol,
    card_code_to_card,
    decode_hand_bitmask,
    map_game_mode,
    SOURCE_SUITS,
    RANK_TO_IDX,
    VALID_BALOOT_INDICES,
    VALID_RANK_RANGE,
)


# ── index_to_card ────────────────────────────────────────────────────

class TestIndexToCard:
    """Test Source index → Card conversion."""

    @pytest.mark.parametrize("idx, expected_suit, expected_rank", [
        # Spades (suit 0): ranks 5-12 → 7,8,9,10,J,Q,K,A
        (0 * 13 + 5, "♠", "7"),
        (0 * 13 + 6, "♠", "8"),
        (0 * 13 + 7, "♠", "9"),
        (0 * 13 + 8, "♠", "10"),
        (0 * 13 + 9, "♠", "J"),
        (0 * 13 + 10, "♠", "Q"),
        (0 * 13 + 11, "♠", "K"),
        (0 * 13 + 12, "♠", "A"),
        # Hearts (suit 1)
        (1 * 13 + 5, "♥", "7"),
        (1 * 13 + 12, "♥", "A"),
        # Clubs (suit 2)
        (2 * 13 + 5, "♣", "7"),
        (2 * 13 + 9, "♣", "J"),
        # Diamonds (suit 3)
        (3 * 13 + 5, "♦", "7"),
        (3 * 13 + 12, "♦", "A"),
    ])
    def test_valid_baloot_indices(self, idx, expected_suit, expected_rank):
        card = index_to_card(idx)
        assert card is not None
        assert card.suit == expected_suit
        assert card.rank == expected_rank

    @pytest.mark.parametrize("idx", [
        0, 1, 2, 3, 4,     # Spades non-Baloot ranks (2-6)
        13, 14, 15, 16, 17, # Hearts non-Baloot ranks (2-6)
        26, 27, 28, 29, 30, # Clubs non-Baloot ranks (2-6)
        39, 40, 41, 42, 43, # Diamonds non-Baloot ranks (2-6)
    ])
    def test_non_baloot_ranks_return_none(self, idx):
        assert index_to_card(idx) is None

    @pytest.mark.parametrize("idx", [-1, -100, 52, 53, 100, 999])
    def test_out_of_range_returns_none(self, idx):
        assert index_to_card(idx) is None

    def test_non_integer_returns_none(self):
        assert index_to_card(5.5) is None  # type: ignore
        assert index_to_card("5") is None  # type: ignore
        assert index_to_card(None) is None  # type: ignore


# ── card_to_index ────────────────────────────────────────────────────

class TestCardToIndex:
    """Test Card → Source index conversion."""

    def test_spades_ace(self):
        assert card_to_index(Card("♠", "A")) == 0 * 13 + 12

    def test_hearts_seven(self):
        assert card_to_index(Card("♥", "7")) == 1 * 13 + 5

    def test_clubs_jack(self):
        assert card_to_index(Card("♣", "J")) == 2 * 13 + 9

    def test_diamonds_ten(self):
        assert card_to_index(Card("♦", "10")) == 3 * 13 + 8

    def test_unknown_suit_raises(self):
        with pytest.raises(ValueError, match="Unknown suit"):
            card_to_index(Card("X", "A"))

    def test_unknown_rank_raises(self):
        with pytest.raises(ValueError, match="Unknown rank"):
            card_to_index(Card("♠", "1"))


# ── Round-trip ───────────────────────────────────────────────────────

class TestRoundTrip:
    """Verify that all 32 valid Baloot indices round-trip correctly."""

    def test_all_32_valid_indices_round_trip(self):
        """Every valid index converts to Card and back to the same index."""
        for idx in sorted(VALID_BALOOT_INDICES):
            card = index_to_card(idx)
            assert card is not None, f"index_to_card({idx}) returned None"
            back = card_to_index(card)
            assert back == idx, f"Round-trip failed: {idx} → {card} → {back}"

    def test_valid_indices_count(self):
        """Exactly 32 valid Baloot indices (4 suits × 8 ranks)."""
        assert len(VALID_BALOOT_INDICES) == 32


# ── suit_idx_to_symbol ───────────────────────────────────────────────

class TestSuitIdxToSymbol:

    def test_all_valid_suits(self):
        assert suit_idx_to_symbol(0) == "♠"
        assert suit_idx_to_symbol(1) == "♥"
        assert suit_idx_to_symbol(2) == "♣"
        assert suit_idx_to_symbol(3) == "♦"

    def test_invalid_suit_returns_question(self):
        assert suit_idx_to_symbol(4) == "?"
        assert suit_idx_to_symbol(-1) == "?"
        assert suit_idx_to_symbol(99) == "?"


# ── card_code_to_card ────────────────────────────────────────────────

class TestCardCodeToCard:
    """Test SEND-event card code parsing."""

    def test_hearts_jack(self):
        card = card_code_to_card("hj")
        assert card is not None
        assert card.suit == "♥"
        assert card.rank == "J"

    def test_spades_10(self):
        card = card_code_to_card("s10")
        assert card is not None
        assert card.suit == "♠"
        assert card.rank == "10"

    def test_diamonds_ace(self):
        card = card_code_to_card("da")
        assert card is not None
        assert card.suit == "♦"
        assert card.rank == "A"

    def test_clubs_seven(self):
        card = card_code_to_card("c7")
        assert card is not None
        assert card.suit == "♣"
        assert card.rank == "7"

    def test_empty_string_returns_none(self):
        assert card_code_to_card("") is None

    def test_single_char_returns_none(self):
        assert card_code_to_card("h") is None

    def test_invalid_suit_returns_none(self):
        assert card_code_to_card("x7") is None

    def test_invalid_rank_returns_none(self):
        assert card_code_to_card("h1") is None  # '1' not in CODE_RANK_MAP


# ── decode_hand_bitmask ──────────────────────────────────────────────

class TestDecodeHandBitmask:

    def test_empty_bitmask(self):
        cards = decode_hand_bitmask(0)
        assert cards == []

    def test_single_card(self):
        # Set bit 5 (index=5 → ♠7)
        bitmask = 1 << 5
        cards = decode_hand_bitmask(bitmask)
        assert len(cards) == 1
        assert cards[0].suit == "♠"
        assert cards[0].rank == "7"

    def test_full_hand_8_cards(self):
        # All 8 spades (indices 5-12)
        bitmask = 0
        for rank_idx in VALID_RANK_RANGE:
            bitmask |= 1 << (0 * 13 + rank_idx)
        cards = decode_hand_bitmask(bitmask)
        assert len(cards) == 8
        suits = {c.suit for c in cards}
        assert suits == {"♠"}

    def test_non_baloot_bits_ignored(self):
        # Set bits for non-Baloot ranks (indices 0-4 of spades)
        bitmask = 0
        for rank_idx in range(5):  # 2, 3, 4, 5, 6
            bitmask |= 1 << (0 * 13 + rank_idx)
        cards = decode_hand_bitmask(bitmask)
        assert cards == []

    def test_mixed_suits(self):
        # ♠A (idx 12) + ♥7 (idx 18) + ♦K (idx 50)
        bitmask = (1 << 12) | (1 << 18) | (1 << 50)
        cards = decode_hand_bitmask(bitmask)
        assert len(cards) == 3
        card_strs = {f"{c.rank}{c.suit}" for c in cards}
        assert "A♠" in card_strs
        assert "7♥" in card_strs
        assert "K♦" in card_strs


# ── map_game_mode ────────────────────────────────────────────────────

class TestMapGameMode:

    def test_ashkal_maps_to_sun(self):
        assert map_game_mode("ashkal") == "SUN"

    def test_sun_maps_to_sun(self):
        assert map_game_mode("sun") == "SUN"

    def test_hokom_maps_to_hokum(self):
        assert map_game_mode("hokom") == "HOKUM"

    def test_hokum_maps_to_hokum(self):
        assert map_game_mode("hokum") == "HOKUM"

    def test_case_insensitive(self):
        assert map_game_mode("ASHKAL") == "SUN"
        assert map_game_mode("HOKOM") == "HOKUM"

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown Source game mode"):
            map_game_mode("freeplay")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            map_game_mode("")
