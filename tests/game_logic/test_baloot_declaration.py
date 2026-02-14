"""
Test Baloot Declaration System
==============================
Tests for BalootManager: K+Q of trump two-phase declaration tracking,
scan logic, point immunity to doubling, mode restrictions, and serialization.

Baloot Rules:
  - HOKUM mode only (no trumps in SUN).
  - Player must hold both K and Q of trump suit at deal time.
  - Phase 1 "Baloot": first K/Q played → announcement (0 GP).
  - Phase 2 "Re-baloot": second K/Q played → 2 GP committed.
  - Points are IMMUNE to doubling (always exactly 2 GP).
"""
import unittest
import json

from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.logic.baloot_manager import BalootManager


def _make_game():
    """Create a 4-player HOKUM game with spades trump."""
    game = Game("test_room")
    game.add_player("p1", "Player 1")  # idx 0, Bottom, us
    game.add_player("p2", "Player 2")  # idx 1, Right, them
    game.add_player("p3", "Player 3")  # idx 2, Top, us
    game.add_player("p4", "Player 4")  # idx 3, Left, them
    game.game_mode = 'HOKUM'
    game.trump_suit = '\u2660'  # spades
    game.declarations = {}
    return game


class TestBalootScanFindsHolder(unittest.TestCase):
    """Tests for scan_initial_hands detecting K+Q holders."""

    def test_scan_finds_holder(self):
        """Player 0 (Bottom) holds both K and Q of trump; scan should detect it."""
        game = _make_game()
        bm = game.baloot_manager

        # Give player 0 both K and Q of trump plus filler cards
        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        # Other players get no trump royals
        for i in [1, 2, 3]:
            game.players[i].hand = [
                Card('\u2665', 'A'),
                Card('\u2665', 'K'),
                Card('\u2666', 'A'),
                Card('\u2666', 'K'),
                Card('\u2663', 'A'),
                Card('\u2663', 'K'),
                Card('\u2660', '7'),
                Card('\u2660', '8'),
            ]

        bm.scan_initial_hands()

        self.assertTrue(
            bm.has_baloot('Bottom'),
            "Bottom should be detected as holding Baloot (K+Q of trump)"
        )

    def test_scan_finds_holder_on_them_team(self):
        """Player 1 (Right, them team) holds K+Q of trump; scan should detect it."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[1].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [0, 2, 3]:
            game.players[i].hand = [
                Card('\u2665', 'A'),
                Card('\u2665', 'K'),
                Card('\u2666', 'A'),
                Card('\u2666', 'K'),
                Card('\u2663', 'A'),
                Card('\u2663', 'K'),
                Card('\u2660', '7'),
                Card('\u2660', '8'),
            ]

        bm.scan_initial_hands()

        self.assertTrue(bm.has_baloot('Right'))
        self.assertFalse(bm.has_baloot('Bottom'))


class TestBalootScanNoHolder(unittest.TestCase):
    """Tests for scan when no player holds both K+Q of trump."""

    def test_scan_no_holder(self):
        """No player has both K and Q of trump; has_baloot should return False for all."""
        game = _make_game()
        bm = game.baloot_manager

        # Split K and Q across different players
        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2665', 'Q'),  # wrong suit Q
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        game.players[1].hand = [
            Card('\u2660', 'Q'),
            Card('\u2665', 'K'),  # wrong suit K
            Card('\u2665', 'A'),
            Card('\u2666', '7'),
            Card('\u2666', '8'),
            Card('\u2663', '9'),
            Card('\u2663', '10'),
            Card('\u2660', '7'),
        ]
        for i in [2, 3]:
            game.players[i].hand = [
                Card('\u2665', 'A'),
                Card('\u2665', '9'),
                Card('\u2666', 'A'),
                Card('\u2666', 'K'),
                Card('\u2663', 'A'),
                Card('\u2663', 'K'),
                Card('\u2660', '8'),
                Card('\u2660', '9'),
            ]

        bm.scan_initial_hands()

        for pos in ['Bottom', 'Right', 'Top', 'Left']:
            self.assertFalse(
                bm.has_baloot(pos),
                f"{pos} should NOT have Baloot when K and Q are split across players"
            )

    def test_scan_king_only(self):
        """Player has only K of trump (no Q); should not be detected as holder."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', '7'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()
        self.assertFalse(bm.has_baloot('Bottom'))


class TestBalootPhase1(unittest.TestCase):
    """Tests for Phase 1 announcement when first K/Q of trump is played."""

    def test_phase1_on_king_played(self):
        """Playing K of trump first should return phase='BALOOT' announcement."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()

        # Play the King of trump
        result = bm.on_card_played('Bottom', Card('\u2660', 'K'))

        self.assertIsNotNone(result, "Playing K of trump should trigger Phase 1")
        self.assertEqual(result['phase'], 'BALOOT')
        self.assertEqual(result['position'], 'Bottom')
        self.assertEqual(result['card_rank'], 'K')
        self.assertEqual(result['game_points'], 0, "Phase 1 should not score any points yet")

    def test_phase1_on_queen_played_first(self):
        """Playing Q of trump first should also trigger Phase 1."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()

        result = bm.on_card_played('Bottom', Card('\u2660', 'Q'))

        self.assertIsNotNone(result)
        self.assertEqual(result['phase'], 'BALOOT')
        self.assertEqual(result['card_rank'], 'Q')

    def test_non_trump_card_returns_none(self):
        """Playing a non-trump card should not trigger any announcement."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()

        result = bm.on_card_played('Bottom', Card('\u2665', '7'))
        self.assertIsNone(result, "Non-trump card should not trigger Baloot phase")


class TestBalootPhase2(unittest.TestCase):
    """Tests for Phase 2 declaration when second K/Q of trump is played."""

    def test_phase2_on_queen_played(self):
        """Playing K then Q of trump should trigger RE_BALOOT with declared=True."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()

        # Phase 1: play King
        bm.on_card_played('Bottom', Card('\u2660', 'K'))

        # Phase 2: play Queen
        result = bm.on_card_played('Bottom', Card('\u2660', 'Q'))

        self.assertIsNotNone(result, "Second trump royal should trigger Phase 2")
        self.assertEqual(result['phase'], 'RE_BALOOT')
        self.assertTrue(result['declared'], "Phase 2 should mark declared=True")
        self.assertEqual(result['game_points'], 2, "RE_BALOOT should award 2 GP")
        self.assertEqual(result['position'], 'Bottom')

    def test_phase2_reversed_order(self):
        """Playing Q then K should also complete the declaration."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()

        bm.on_card_played('Bottom', Card('\u2660', 'Q'))
        result = bm.on_card_played('Bottom', Card('\u2660', 'K'))

        self.assertIsNotNone(result)
        self.assertEqual(result['phase'], 'RE_BALOOT')
        self.assertTrue(result['declared'])

    def test_third_play_after_declaration_ignored(self):
        """After both K and Q are played, further plays should return None."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()

        bm.on_card_played('Bottom', Card('\u2660', 'K'))
        bm.on_card_played('Bottom', Card('\u2660', 'Q'))

        # Any subsequent call should be ignored
        result = bm.on_card_played('Bottom', Card('\u2660', 'K'))
        self.assertIsNone(result, "Already declared; further plays should be ignored")


class TestBalootPointsImmunity(unittest.TestCase):
    """Tests that Baloot GP are immune to doubling multipliers."""

    def test_points_immune_to_doubling(self):
        """After declaration, get_baloot_points() should always return 2 GP regardless of doubling level."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()
        bm.on_card_played('Bottom', Card('\u2660', 'K'))
        bm.on_card_played('Bottom', Card('\u2660', 'Q'))

        # Test at various doubling levels
        for level in [1, 2, 3, 4, 100]:
            game.doubling_level = level
            points = bm.get_baloot_points()
            self.assertEqual(
                points,
                {'us': 2, 'them': 0},
                f"Baloot GP must be exactly 2 at doubling level {level}, got {points}"
            )

    def test_points_zero_before_declaration(self):
        """Before any declaration, get_baloot_points should return 0 for both teams."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()

        points = bm.get_baloot_points()
        self.assertEqual(points, {'us': 0, 'them': 0})

    def test_points_zero_after_only_phase1(self):
        """After only Phase 1 (one card played), GP should still be 0."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()
        bm.on_card_played('Bottom', Card('\u2660', 'K'))

        points = bm.get_baloot_points()
        self.assertEqual(points, {'us': 0, 'them': 0},
                         "Only Phase 1 completed; no GP should be awarded yet")


class TestSunModeNoBaloot(unittest.TestCase):
    """Tests that Baloot does not apply in SUN mode."""

    def test_sun_mode_no_baloot(self):
        """In SUN mode, scan_initial_hands should find nothing (no trump in SUN)."""
        game = _make_game()
        game.game_mode = 'SUN'
        game.trump_suit = None
        bm = game.baloot_manager

        # Even if a player has K+Q of spades, SUN has no trump
        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()

        for pos in ['Bottom', 'Right', 'Top', 'Left']:
            self.assertFalse(
                bm.has_baloot(pos),
                f"SUN mode should never detect Baloot holders ({pos})"
            )

    def test_sun_mode_on_card_played_returns_none(self):
        """In SUN mode, on_card_played should always return None."""
        game = _make_game()
        game.game_mode = 'SUN'
        game.trump_suit = None
        bm = game.baloot_manager

        result = bm.on_card_played('Bottom', Card('\u2660', 'K'))
        self.assertIsNone(result, "SUN mode should not track Baloot plays")

    def test_sun_mode_get_baloot_points_zero(self):
        """In SUN mode, get_baloot_points should always return zeroes."""
        game = _make_game()
        game.game_mode = 'SUN'
        game.trump_suit = None
        bm = game.baloot_manager

        points = bm.get_baloot_points()
        self.assertEqual(points, {'us': 0, 'them': 0})


class TestBalootReset(unittest.TestCase):
    """Tests that reset() clears all Baloot state."""

    def test_reset_clears_state(self):
        """After a full declaration, reset() should clear everything."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()
        bm.on_card_played('Bottom', Card('\u2660', 'K'))
        bm.on_card_played('Bottom', Card('\u2660', 'Q'))

        # Verify declaration happened
        self.assertEqual(bm.get_baloot_points(), {'us': 2, 'them': 0})
        self.assertEqual(len(bm.get_declarations()), 1)

        # Reset
        bm.reset()

        # After reset, everything should be cleared
        self.assertEqual(bm.get_baloot_points(), {'us': 0, 'them': 0})
        self.assertEqual(bm.get_declarations(), [])
        self.assertFalse(bm.has_baloot('Bottom'))

        state = bm.get_state()
        self.assertEqual(state['holders'], [])
        self.assertEqual(state['phase1'], [])
        self.assertEqual(state['declared'], [])

    def test_reset_allows_new_scan(self):
        """After reset, a new scan should detect holders from current hands."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()
        bm.on_card_played('Bottom', Card('\u2660', 'K'))
        bm.on_card_played('Bottom', Card('\u2660', 'Q'))
        bm.reset()

        # Re-scan with new hands (player 2 now has K+Q)
        game.players[0].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]
        game.players[2].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]

        bm.scan_initial_hands()
        self.assertTrue(bm.has_baloot('Top'))
        self.assertFalse(bm.has_baloot('Bottom'))


class TestBalootSerialization(unittest.TestCase):
    """Tests for get_state() serialization round-trip."""

    def test_serialization_round_trip(self):
        """get_state() should return a JSON-serializable dict."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()
        bm.on_card_played('Bottom', Card('\u2660', 'K'))
        bm.on_card_played('Bottom', Card('\u2660', 'Q'))

        state = bm.get_state()

        # Must be a dict
        self.assertIsInstance(state, dict)

        # Must contain expected keys
        self.assertIn('holders', state)
        self.assertIn('phase1', state)
        self.assertIn('declared', state)

        # Must be JSON serializable
        try:
            serialized = json.dumps(state)
            deserialized = json.loads(serialized)
        except (TypeError, ValueError) as e:
            self.fail(f"get_state() is not JSON-serializable: {e}")

        # Round-trip should produce equivalent data
        self.assertEqual(set(deserialized['holders']), set(state['holders']))
        self.assertEqual(set(deserialized['phase1']), set(state['phase1']))
        self.assertEqual(set(deserialized['declared']), set(state['declared']))

    def test_serialization_empty_state(self):
        """Empty state (no scan) should also be serializable."""
        game = _make_game()
        bm = game.baloot_manager

        state = bm.get_state()
        serialized = json.dumps(state)
        deserialized = json.loads(serialized)

        self.assertEqual(deserialized['holders'], [])
        self.assertEqual(deserialized['phase1'], [])
        self.assertEqual(deserialized['declared'], [])

    def test_serialization_partial_state(self):
        """State after Phase 1 only (no Phase 2) should be serializable."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()
        bm.on_card_played('Bottom', Card('\u2660', 'K'))

        state = bm.get_state()
        serialized = json.dumps(state)
        deserialized = json.loads(serialized)

        self.assertIn('Bottom', deserialized['holders'])
        self.assertIn('Bottom', deserialized['phase1'])
        self.assertEqual(deserialized['declared'], [])


class TestBalootGetDeclarations(unittest.TestCase):
    """Tests for get_declarations() list output."""

    def test_declarations_after_full_baloot(self):
        """get_declarations should return a list with one entry after one player completes Baloot."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()
        bm.on_card_played('Bottom', Card('\u2660', 'K'))
        bm.on_card_played('Bottom', Card('\u2660', 'Q'))

        decls = bm.get_declarations()
        self.assertEqual(len(decls), 1)
        self.assertEqual(decls[0]['type'], 'BALOOT')
        self.assertEqual(decls[0]['position'], 'Bottom')
        self.assertEqual(decls[0]['team'], 'us')
        self.assertEqual(decls[0]['game_points'], 2)
        self.assertEqual(decls[0]['abnat'], 20)

    def test_declarations_empty_before_completion(self):
        """Before Phase 2, get_declarations should return empty list."""
        game = _make_game()
        bm = game.baloot_manager

        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        for i in [1, 2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()
        bm.on_card_played('Bottom', Card('\u2660', 'K'))

        self.assertEqual(bm.get_declarations(), [])


class TestBalootNonHolder(unittest.TestCase):
    """Tests that non-holders do not trigger Baloot phases."""

    def test_non_holder_king_play_ignored(self):
        """A player who does NOT hold both K+Q should not trigger Baloot on card play."""
        game = _make_game()
        bm = game.baloot_manager

        # Player 0 has only K of trump (no Q)
        game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', '7'),
            Card('\u2665', '7'),
            Card('\u2665', '8'),
            Card('\u2666', '9'),
            Card('\u2666', '10'),
            Card('\u2663', 'A'),
            Card('\u2663', 'J'),
        ]
        # Player 1 has the Q (split)
        game.players[1].hand = [
            Card('\u2660', 'Q'),
            Card('\u2660', '8'),
            Card('\u2665', 'A'),
            Card('\u2666', '7'),
            Card('\u2666', '8'),
            Card('\u2663', '9'),
            Card('\u2663', '10'),
            Card('\u2663', 'K'),
        ]
        for i in [2, 3]:
            game.players[i].hand = [Card('\u2665', str(r)) for r in ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']]

        bm.scan_initial_hands()

        result = bm.on_card_played('Bottom', Card('\u2660', 'K'))
        self.assertIsNone(result, "Non-holder should not trigger Baloot")

        result = bm.on_card_played('Right', Card('\u2660', 'Q'))
        self.assertIsNone(result, "Non-holder should not trigger Baloot")


if __name__ == '__main__':
    unittest.main()
