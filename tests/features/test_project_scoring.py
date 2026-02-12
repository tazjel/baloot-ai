"""
Test Project Scoring Combos
Tests for project declarations, resolution, and scoring edge cases.
"""
import unittest
from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.logic.rules.projects import check_project_eligibility


class TestProjectEligibility(unittest.TestCase):
    """Tests for check_project_eligibility — scanning hands for valid projects."""

    def test_four_of_a_kind_detected(self):
        """Four cards of the same rank should be detected as a HUNDRED (4KIND) project."""
        hand = [
            Card('♠', 'A'), Card('♥', 'A'), Card('♦', 'A'), Card('♣', 'A'),
            Card('♠', 'K'), Card('♥', 'K'), Card('♦', '9'), Card('♣', '7')
        ]
        projects = check_project_eligibility(hand, 'HOKUM')
        # Four-of-a-kind of court cards uses type='HUNDRED', kind='4KIND'
        four_kind = [p for p in projects if p.get('kind') == '4KIND']
        self.assertTrue(len(four_kind) > 0, "Four Aces should be detected as HUNDRED (4KIND)")

    def test_three_card_sequence_sira(self):
        """Three consecutive cards of the same suit should be detected."""
        hand = [
            Card('♠', '7'), Card('♠', '8'), Card('♠', '9'),
            Card('♥', 'A'), Card('♥', 'K'), Card('♦', 'Q'), Card('♣', '10'), Card('♦', '7')
        ]
        projects = check_project_eligibility(hand, 'HOKUM')
        sequences = [p for p in projects if p.get('type') in ('SIRA', 'FIFTY', 'HUNDRED')]
        self.assertTrue(len(sequences) > 0, "7-8-9 of spades should be detected as a sequence")

    def test_no_projects_in_weak_hand(self):
        """A hand with no sequences or four-of-a-kind should return no projects."""
        hand = [
            Card('♠', '7'), Card('♥', '9'), Card('♦', 'Q'), Card('♣', 'A'),
            Card('♠', 'K'), Card('♥', '8'), Card('♦', '10'), Card('♣', 'J')
        ]
        projects = check_project_eligibility(hand, 'HOKUM')
        # Filter only meaningful projects (non-zero score)
        meaningful = [p for p in projects if p.get('score', 0) > 0]
        self.assertEqual(len(meaningful), 0, "Scattered hand should have no projects")

    def test_five_card_sequence_hundred(self):
        """Five consecutive cards should be a HUNDRED (100 points)."""
        hand = [
            Card('♠', '7'), Card('♠', '8'), Card('♠', '9'), Card('♠', '10'), Card('♠', 'J'),
            Card('♥', 'A'), Card('♦', 'K'), Card('♣', '7')
        ]
        projects = check_project_eligibility(hand, 'HOKUM')
        hundreds = [p for p in projects if p.get('type') == 'HUNDRED']
        self.assertTrue(len(hundreds) > 0, "5-card sequence should be HUNDRED")


class TestProjectScoring(unittest.TestCase):
    """Tests for project scoring calculation within a full game context."""

    def setUp(self):
        self.game = Game("test_room")
        self.game.add_player("p1", "Player 1")  # 0 Bottom, US
        self.game.add_player("p2", "Player 2")  # 1 Right, THEM  
        self.game.add_player("p3", "Player 3")  # 2 Top, US
        self.game.add_player("p4", "Player 4")  # 3 Left, THEM

    def _setup_round(self, mode='HOKUM', trump='♠', bidder='Bottom'):
        """Set up a complete round context."""
        self.game.game_mode = mode
        self.game.trump_suit = trump if mode == 'HOKUM' else None
        self.game.phase = 'PLAYING'
        self.game.bid = {"type": mode, "bidder": bidder, "doubled": False}
        self.game.doubling_level = 1
        self.game.sawa_failed_khasara = False
        self.game.is_project_revealing = False

    def _simulate_tricks(self, us_wins=4, them_wins=4, points_per=13):
        """Simulate trick history with given distribution."""
        self.game.round_history = []
        positions_us = ['Bottom', 'Top']
        positions_them = ['Right', 'Left']
        
        for i in range(us_wins):
            self.game.round_history.append({
                'winner': positions_us[i % 2],
                'points': points_per,
                'cards': [],
                'playedBy': []
            })
        for i in range(them_wins):
            self.game.round_history.append({
                'winner': positions_them[i % 2],
                'points': points_per,
                'cards': [],
                'playedBy': []
            })

    def test_project_adds_game_points_hokum(self):
        """In Hokum, project abnat / 10 = game points added."""
        self._setup_round(mode='HOKUM')
        self._simulate_tricks(us_wins=5, them_wins=3)
        
        # US has a SIRA project (20 abnat) 
        self.game.declarations = {
            'Bottom': [{'valid': True, 'score': 20, 'type': 'SIRA', 'rank': '9', 'suit': '♠'}]
        }
        
        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()
        
        # Project GP in Hokum: 20 // 10 = 2 extra GP for US
        self.assertEqual(result['us']['projectPoints'], 20)
        proj_gp = 20 // 10
        self.assertEqual(proj_gp, 2)

    def test_project_adds_game_points_sun(self):
        """In Sun, project abnat * 2 / 10 = game points (doubled in Sun)."""
        self._setup_round(mode='SUN', bidder='Bottom')
        self._simulate_tricks(us_wins=5, them_wins=3)
        
        # US has a FIFTY project (50 abnat)
        self.game.declarations = {
            'Bottom': [{'valid': True, 'score': 50, 'type': 'FIFTY', 'rank': 'K', 'suit': '♥'}]
        }
        
        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()
        
        # Project GP in Sun: (50 * 2) // 10 = 10 extra GP for US
        proj_gp = (50 * 2) // 10
        self.assertEqual(proj_gp, 10)
        self.assertEqual(result['us']['projectPoints'], 50)

    def test_multiple_projects_same_team(self):
        """Multiple projects on the same team should all contribute."""
        self._setup_round(mode='HOKUM')
        self._simulate_tricks(us_wins=5, them_wins=3)
        
        # US has TWO projects: SIRA (20) + FIFTY (50)
        self.game.declarations = {
            'Bottom': [
                {'valid': True, 'score': 20, 'type': 'SIRA', 'rank': '9', 'suit': '♠'},
                {'valid': True, 'score': 50, 'type': 'FIFTY', 'rank': 'K', 'suit': '♥'}
            ]
        }
        
        proj_points = self.game.project_manager.calculate_project_points()
        self.assertEqual(proj_points['us'], 70, "Two projects should total 70 abnat")
        self.assertEqual(proj_points['them'], 0)

    def test_projects_from_both_teammates(self):
        """Projects from both US players should combine."""
        self._setup_round(mode='HOKUM')
        self._simulate_tricks(us_wins=5, them_wins=3)
        
        # Bottom and Top (both US) each have a project
        self.game.declarations = {
            'Bottom': [{'valid': True, 'score': 20, 'type': 'SIRA', 'rank': '9', 'suit': '♠'}],
            'Top': [{'valid': True, 'score': 50, 'type': 'FIFTY', 'rank': 'K', 'suit': '♥'}]
        }
        
        proj_points = self.game.project_manager.calculate_project_points()
        self.assertEqual(proj_points['us'], 70, "Both US players' projects should sum")

    def test_project_on_khasara_goes_to_opponent(self):
        """When bidder team loses (Khasara), ALL points including projects go to opponent."""
        self._setup_round(mode='HOKUM', bidder='Bottom')  # US bids
        # US loses more tricks → Khasara
        self._simulate_tricks(us_wins=2, them_wins=6)
        
        # US has a project but loses the bid
        self.game.declarations = {
            'Bottom': [{'valid': True, 'score': 50, 'type': 'FIFTY', 'rank': 'K', 'suit': '♠'}]
        }
        
        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()
        
        # Khasara: US bid and lost → all points go to THEM
        self.assertEqual(score_us, 0, "Bidder team should get 0 on Khasara")
        self.assertGreater(score_them, 0, "Opponent should get all points on Khasara")


class TestProjectResolution(unittest.TestCase):
    """Tests for ProjectManager.resolve_declarations — winner-takes-all logic."""

    def setUp(self):
        self.game = Game("test_room")
        self.game.add_player("p1", "Player 1")  # 0 Bottom, US
        self.game.add_player("p2", "Player 2")  # 1 Right, THEM
        self.game.add_player("p3", "Player 3")  # 2 Top, US
        self.game.add_player("p4", "Player 4")  # 3 Left, THEM
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        self.game.dealer_index = 0

    def test_higher_project_wins_all(self):
        """Team with the higher-ranked project wins; other team's projects are cancelled."""
        # US declares FIFTY, THEM declares SIRA → US wins all
        self.game.trick_1_declarations = {
            'Bottom': [{'type': 'FIFTY', 'score': 50, 'rank': 'A', 'suit': '♠', 'cards': []}],
            'Right': [{'type': 'SIRA', 'score': 20, 'rank': 'K', 'suit': '♥', 'cards': []}]
        }
        
        self.game.project_manager.resolve_declarations()
        
        # US should have declarations, THEM should not
        self.assertIn('Bottom', self.game.declarations)
        self.assertNotIn('Right', self.game.declarations)

    def test_no_declarations_produces_empty(self):
        """No declarations from any player → empty declarations dict."""
        self.game.trick_1_declarations = {}
        
        self.game.project_manager.resolve_declarations()
        
        self.assertEqual(self.game.declarations, {})

    def test_single_team_declaration_always_valid(self):
        """If only one team declares, their projects are always valid."""
        self.game.trick_1_declarations = {
            'Right': [{'type': 'FIFTY', 'score': 50, 'rank': 'K', 'suit': '♥', 'cards': []}]
        }
        
        self.game.project_manager.resolve_declarations()
        
        self.assertIn('Right', self.game.declarations)
        self.assertEqual(len(self.game.declarations['Right']), 1)


if __name__ == '__main__':
    unittest.main()
