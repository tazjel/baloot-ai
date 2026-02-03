import pytest
from unittest.mock import MagicMock, patch
from game_engine.logic.game import Game, GamePhase
from game_engine.models.player import Player

class TestQaydTrigger:
    @pytest.fixture
    def game(self):
        g = Game("test_room")
        for i in range(4):
            g.add_player(f"p{i}", f"Player{i}")
        g.start_game()
        g.phase = GamePhase.PLAYING.value
        # Ensure hand is not empty
        g.players[0].hand = [MagicMock(rank='A', suit='♠')] 
        return g

    def test_auto_play_card_triggers_qayd_on_accusation_in_playing_phase(self, game):
        """
        When bot decides QAYD_ACCUSATION in PLAYING phase, 
        it should TRIGGER investigation first (transition to CHALLENGE), 
        not confirm immediately.
        """
        with patch('ai_worker.agent.bot_agent') as mock_bot:
            # Mock bot decision to be ACCUSATION
            mock_bot.get_decision.return_value = {
                'action': 'QAYD_ACCUSATION',
                'accusation': {'reason': 'test'}
            }
            
            # Mock handle_qayd_trigger to verify it is called
            # We can also check if phase changes if we don't mock it, 
            # but mocking ensures we hit the right code path.
            # However, Game.handle_qayd_trigger delegates to ChallengePhase.
            # Let's spy on ChallengePhase.trigger_investigation
            
            with patch.object(game.challenge_phase, 'trigger_investigation', return_value={'success': True}) as mock_trigger:
                result = game.auto_play_card(0)
                
                # Assertions
                mock_trigger.assert_called_once()
                assert result == {'success': True}
                
    def test_auto_play_card_processes_accusation_in_challenge_phase(self, game):
        """
        When bot decides QAYD_ACCUSATION in CHALLENGE phase,
        it should process the accusation (confirm/verify).
        """
        game.phase = GamePhase.CHALLENGE.value
        
        with patch('ai_worker.agent.bot_agent') as mock_bot:
            mock_bot.get_decision.return_value = {
                'action': 'QAYD_ACCUSATION',
                'accusation': {'reason': 'test'}
            }
            
            with patch.object(game, 'process_accusation', return_value={'success': True}) as mock_process:
                game.auto_play_card(0)
                mock_process.assert_called_once()

    def test_auto_play_card_triggers_qayd_explicitly(self, game):
        """
        When bot decides QAYD_TRIGGER, it should call trigger_investigation.
        """
        with patch('ai_worker.agent.bot_agent') as mock_bot:
            mock_bot.get_decision.return_value = {'action': 'QAYD_TRIGGER'}
            
            with patch.object(game.challenge_phase, 'trigger_investigation', return_value={'success': True}) as mock_trigger:
                game.auto_play_card(0)
                mock_trigger.assert_called_once()
