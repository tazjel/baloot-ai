
import unittest
from unittest.mock import MagicMock, patch
from game_engine.logic.qayd_engine import QaydEngine, QaydStep, QaydMenuOption
from game_engine.logic.rules_validator import RulesValidator

class TestQaydProof(unittest.TestCase):
    def setUp(self):
        # Mock Game
        self.mock_game = MagicMock()
        self.mock_game.players = [
            MagicMock(position='Bottom', team='us', index=0),
            MagicMock(position='Right', team='them', index=1),
            MagicMock(position='Top', team='us', index=2),
            MagicMock(position='Left', team='them', index=3)
        ]
        self.mock_game.is_locked = False
        self.mock_game.phase = 'PLAYING'
        self.mock_game.timer_paused = False
        self.mock_game.state.resolved_crimes = []
        self.mock_game.game_mode = 'SUN'
        self.mock_game.doubling_level = 1
        self.mock_game.round_history = []
        self.mock_game.table_cards = []
        
        # Engine
        self.engine = QaydEngine(self.mock_game)

    def test_handle_bot_accusation_revoke(self):
        """Test that handle_bot_accusation correctly processes a valid Revoke accusation"""
        
        # Setup: Bot (Right) accuses Player (Bottom) of Revoke
        accuser_idx = 1
        offender_pos = 'Bottom'
        
        # Crime: Bottom played Diamonds (D) when Hearts (H) was led, but has H.
        crime_card = {'suit': 'D', 'rank': '10', 'played_by': 'Bottom', 'trick_idx': 0, 'card_idx': 1}
        # Proof: Bottom later played Hearts (H)
        proof_card = {'suit': 'H', 'rank': '7', 'played_by': 'Bottom', 'trick_idx': 1, 'card_idx': 0}
        
        accusation_payload = {
            'violation_type': 'REVOKE',
            'crime_card': crime_card,
            'proof_card': proof_card
        }
        
        # Mock Validator to return Guilty
        with patch('game_engine.logic.rules_validator.RulesValidator.validate') as mock_validate:
             mock_validate.return_value = (True, 'Revoke Confirmed')
             
             # Mock Validation Helper
             self.engine._validate_card_in_history = MagicMock(return_value=True)
             
             # Execute
             res = self.engine.handle_bot_accusation(accuser_idx, accusation_payload)
             
             # Assertions
             self.assertTrue(res['success'])
             self.assertEqual(self.engine.state['step'], QaydStep.RESULT)
             self.assertEqual(self.engine.state['verdict'], 'CORRECT')
             self.assertEqual(self.engine.state['loser_team'], 'us') # Offender is Bottom (us)
             self.assertEqual(self.engine.state['violation_type'], 'REVOKE')
             
             # Verify state machine flow
             self.assertTrue(self.engine.state['active'])
             self.assertEqual(self.engine.state['reporter'], 'Right')
             
             # Verify Penalty Logic (Sun = 26) since doubled=1 (default)
             self.assertEqual(self.engine.state['penalty_points'], 26)

    def test_handle_bot_accusation_invalid_proof(self):
        """Test that invalid proof results in failure response (though engine handles it via validator usually)"""
        # If validator returns False
        
        accuser_idx = 1
        crime_card = {'suit': 'D', 'rank': '10', 'played_by': 'Bottom', 'trick_idx': 0, 'card_idx': 1}
        proof_card = {'suit': 'S', 'rank': 'A', 'played_by': 'Bottom', 'trick_idx': 1, 'card_idx': 0}
        
        accusation_payload = {
            'violation_type': 'REVOKE',
            'crime_card': crime_card,
            'proof_card': proof_card
        }
        
        with patch('game_engine.logic.rules_validator.RulesValidator.validate') as mock_validate:
             mock_validate.return_value = (False, 'Not a revoke')
             self.engine._validate_card_in_history = MagicMock(return_value=True)
             
             res = self.engine.handle_bot_accusation(accuser_idx, accusation_payload)
             
             self.assertTrue(res['success'])
             self.assertEqual(self.engine.state['verdict'], 'WRONG')
             self.assertEqual(self.engine.state['loser_team'], 'them') # Reporter loses

    def test_real_validator_integration(self):
        """Test with REAL RulesValidator to ensure proof logic works end-to-end"""
        # 1. Setup History
        # Round: SUN.
        # Trick 0: Left leads H7. Bottom (Me) has H10 but plays D9 (Revoke).
        # Trick 1: Bottom leads H10 (Proof).
        
        # Helper to make card dicts
        def card(s, r): return {'suit': s, 'rank': r}
        
        self.mock_game.trump_suit = 'SUN'
        self.mock_game.game_mode = 'SUN'
        
        # Trick 0 History
        t0 = {
            'cards': [
                {'card': card('H', '7'), 'playedBy': 'Left'},   # Lead
                {'card': card('D', '9'), 'playedBy': 'Bottom'}, # Revoke! (Assuming Bottom has H)
                {'card': card('H', 'K'), 'playedBy': 'Right'},
                {'card': card('H', 'A'), 'playedBy': 'Top'}
            ],
            'winner': 'Top',
            'leader': 'Left'
        }
        
        # Trick 1 (Current or Past)
        t1 = {
             'cards': [
                 {'card': card('H', '10'), 'playedBy': 'Bottom'}, # Proof! Shows I had H all along.
             ]
        }
        
        # Mock Game State needed by Validator
        self.mock_game.round_history = [t0]
        # RulesValidator uses table_cards for the current trick (index 1)
        self.mock_game.table_cards = t1['cards']
        self.mock_game.players[0].hand = [] # Relevant for current check? No, history check.
        
        # Validator needs to know WHO we are accusing.
        # QaydEngine calls validator.validate(violation, crime_card, proof_card, accuser, offender)
        
        # 2. Construct Payload
        crime = {'suit': 'D', 'rank': '9', 'played_by': 'Bottom', 'trick_idx': 0, 'card_idx': 1}
        proof = {'suit': 'H', 'rank': '10', 'played_by': 'Bottom', 'trick_idx': 1, 'card_idx': 0} # 1 is current?
        
        # We need to ensure validator can access this card in history.
        # RulesValidator uses `game.round_history`.
        
        # No need to instantiate RulesValidator as it is static and hardcoded in QaydEngine.
        # QaydEngine will call RulesValidator.validate(ctx) using the real class.
        
        # 3. Execute
        # We need to simulate that proof card is indeed in history/hand?
        # If trick 1 is "current", it might not be in round_history yet.
        # But QaydEngine adds 'current_trick' logic? 
        # Actually validation logic usually checks `played_cards`.
        
        # Let's put Proof in history for simplicity (Trick 1 finished)
        self.mock_game.round_history.append(t1)
        
        res = self.engine.handle_bot_accusation(1, { # Right accuses
            'violation_type': 'REVOKE',
            'crime_card': crime,
            'proof_card': proof
        })
        
        # 4. Assert
        # This will fail if RulesValidator logic (find_card, _validate_revoke) is broken.
        self.assertTrue(res['success'], f"Validation failed: {res.get('error')}")
        self.assertEqual(self.engine.state['verdict'], 'CORRECT')
        self.assertEqual(self.engine.state['violation_type'], 'REVOKE')

if __name__ == '__main__':
    unittest.main()

