"""
Test Project Manager
Tests for ProjectManager: project declaration, eligibility, resolve_declarations,
and calculate_project_points.
"""
import unittest
from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.models.constants import GamePhase


class _ProjectTestBase(unittest.TestCase):
    """Base: Game in PLAYING phase with hands assigned."""

    def setUp(self):
        self.game = Game("test_room")
        for i in range(4):
            self.game.add_player(f"p{i}", f"Player {i}")
        self.game.lifecycle.start_game()
        # Force to PLAYING
        self.game.phase = GamePhase.PLAYING.value
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        self.game.current_turn = 0
        self.game.round_history = []
        self.game.table_cards = []
        self.game.trick_1_declarations = {}
        self.game.declarations = {}

    def _give_sira_hand(self, player_index, suit='♥'):
        """Give a SIRA (3 consecutive same-suit) hand."""
        self.game.players[player_index].hand = [
            Card(suit, 'A'), Card(suit, 'K'), Card(suit, 'Q'),
            Card('♣', '7'), Card('♣', '9'), Card('♣', 'J'),
            Card('♦', '7'), Card('♦', '9')
        ]

    def _give_fifty_hand(self, player_index, suit='♥'):
        """Give a FIFTY (4 consecutive same-suit) hand."""
        self.game.players[player_index].hand = [
            Card(suit, 'A'), Card(suit, 'K'), Card(suit, 'Q'),
            Card(suit, 'J'), Card('♣', '7'), Card('♣', '8'),
            Card('♦', '7'), Card('♦', '8')
        ]

    def _give_hundred_hand(self, player_index):
        """Give a HUNDRED (4 of a kind of K/Q/J/10/A) hand."""
        self.game.players[player_index].hand = [
            Card('♠', 'K'), Card('♥', 'K'), Card('♦', 'K'),
            Card('♣', 'K'), Card('♠', '7'), Card('♥', '7'),
            Card('♦', '7'), Card('♣', '8')
        ]


class TestProjectDeclaration(_ProjectTestBase):
    """Tests for handle_declare_project."""

    def test_declare_sira_success(self):
        """Valid SIRA declaration should succeed."""
        self._give_sira_hand(0)
        result = self.game.project_manager.handle_declare_project(0, 'SIRA')
        self.assertIn('success', result)

    def test_declare_fifty_success(self):
        """Valid FIFTY declaration should succeed."""
        self._give_fifty_hand(0)
        result = self.game.project_manager.handle_declare_project(0, 'FIFTY')
        self.assertIn('success', result)

    def test_declare_hundred_success(self):
        """Valid HUNDRED (four of a kind) declaration should succeed."""
        self._give_hundred_hand(0)
        result = self.game.project_manager.handle_declare_project(0, 'HUNDRED')
        self.assertIn('success', result)

    def test_declare_invalid_project_rejected(self):
        """Declaring a project the hand doesn't support should fail."""
        # Give a hand with no projects
        self.game.players[0].hand = [
            Card('♠', '7'), Card('♥', '8'), Card('♦', '9'),
            Card('♣', '7'), Card('♠', '9'), Card('♥', '7'),
            Card('♦', '8'), Card('♣', '9')
        ]
        result = self.game.project_manager.handle_declare_project(0, 'SIRA')
        self.assertIn('error', result)

    def test_duplicate_declaration_ignored(self):
        """Declaring the same project twice should not duplicate."""
        self._give_sira_hand(0)
        self.game.project_manager.handle_declare_project(0, 'SIRA')
        self.game.project_manager.handle_declare_project(0, 'SIRA')
        pos = self.game.players[0].position
        count = len(self.game.trick_1_declarations.get(pos, []))
        # Should only have 1 entry (deduplicated)
        self.assertEqual(count, 1)

    def test_wrong_turn_rejected(self):
        """Can only declare on your turn (trick 0 only)."""
        self._give_sira_hand(0)
        self.game.current_turn = 1  # Not player 0's turn
        result = self.game.project_manager.handle_declare_project(0, 'SIRA')
        self.assertIn('error', result)


class TestProjectResolution(_ProjectTestBase):
    """Tests for resolve_declarations."""

    def test_resolve_no_declarations(self):
        """Resolving with no declarations should clear declarations."""
        self.game.project_manager.resolve_declarations()
        self.assertEqual(self.game.declarations, {})

    def test_resolve_single_team_wins(self):
        """Single team with projects should win them all."""
        self._give_sira_hand(0)
        self.game.project_manager.handle_declare_project(0, 'SIRA')
        self.game.project_manager.resolve_declarations()
        pos = self.game.players[0].position
        self.assertIn(pos, self.game.declarations)

    def test_resolve_higher_beats_lower(self):
        """Higher project should beat lower one from opposing team."""
        # Player 0 (us team) has FIFTY
        self._give_fifty_hand(0, '♥')
        self.game.project_manager.handle_declare_project(0, 'FIFTY')

        # Player 1 (them team) has SIRA
        self._give_sira_hand(1, '♦')
        self.game.current_turn = 1
        self.game.project_manager.handle_declare_project(1, 'SIRA')

        self.game.project_manager.resolve_declarations()

        # FIFTY > SIRA, so Player 0's team should win
        pos0 = self.game.players[0].position
        pos1 = self.game.players[1].position
        self.assertIn(pos0, self.game.declarations)
        self.assertNotIn(pos1, self.game.declarations)

    def test_reveal_flag_set(self):
        """After resolving, is_project_revealing should be True."""
        self._give_sira_hand(0)
        self.game.project_manager.handle_declare_project(0, 'SIRA')
        self.game.project_manager.resolve_declarations()
        self.assertTrue(self.game.is_project_revealing)


class TestProjectPointCalculation(_ProjectTestBase):
    """Tests for calculate_project_points."""

    def test_no_declarations_zero_points(self):
        """No declarations should result in zero points."""
        points = self.game.project_manager.calculate_project_points()
        self.assertEqual(points['us'], 0)
        self.assertEqual(points['them'], 0)

    def test_sira_gives_20_points(self):
        """SIRA should give 20 abnat points."""
        self._give_sira_hand(0)
        self.game.project_manager.handle_declare_project(0, 'SIRA')
        self.game.project_manager.resolve_declarations()
        points = self.game.project_manager.calculate_project_points()
        team = self.game.players[0].team
        self.assertEqual(points[team], 20)

    def test_fifty_gives_50_points(self):
        """FIFTY project should give 50 points."""
        self._give_fifty_hand(0)
        self.game.project_manager.handle_declare_project(0, 'FIFTY')
        self.game.project_manager.resolve_declarations()
        points = self.game.project_manager.calculate_project_points()
        team = self.game.players[0].team
        self.assertEqual(points[team], 50)

    def test_hundred_gives_100_points(self):
        """HUNDRED project should give 100 points."""
        self._give_hundred_hand(0)
        self.game.project_manager.handle_declare_project(0, 'HUNDRED')
        self.game.project_manager.resolve_declarations()
        points = self.game.project_manager.calculate_project_points()
        team = self.game.players[0].team
        self.assertEqual(points[team], 100)


class TestAutoDeclareBotProjects(_ProjectTestBase):
    """Tests for auto_declare_bot_projects."""

    def test_auto_declare_finds_projects(self):
        """Bots with eligible hands should have projects auto-declared."""
        self.game.players[1].is_bot = True
        self._give_sira_hand(1)
        # Pre-clear to avoid hitting the sanitize-dedup bug
        self.game.trick_1_declarations = {}
        self.game.declarations = {}
        self.game.project_manager.auto_declare_bot_projects()
        pos = self.game.players[1].position
        has_decl = pos in self.game.trick_1_declarations and len(self.game.trick_1_declarations[pos]) > 0
        self.assertTrue(has_decl)

    def test_auto_declare_skips_humans(self):
        """Human players should not have projects auto-declared."""
        self.game.players[0].is_bot = False
        self._give_sira_hand(0)
        self.game.project_manager.auto_declare_bot_projects()
        pos = self.game.players[0].position
        has_decl = pos in self.game.trick_1_declarations and len(self.game.trick_1_declarations[pos]) > 0
        self.assertFalse(has_decl)


if __name__ == '__main__':
    unittest.main()
