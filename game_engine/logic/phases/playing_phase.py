import logging
from typing import Dict, Optional, Any

from game_engine.logic.phases.challenge_phase import GamePhase

logger = logging.getLogger(__name__)

class PlayingPhase:
    """
    Handles the PLAYING phase logic (Trick taking).
    """

    def __init__(self, game_instance):
        self.game = game_instance

    def play_card(self, player_index: int, card_idx: int, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Orchestrates playing a card.
        """
        if self.game.phase != GamePhase.PLAYING.value:
             return {'success': False, 'error': f"Not in playing phase (Current: {self.game.phase})"}
        
        # 1. Validate turn
        if player_index != self.game.current_player_index:
             return {'success': False, 'error': 'Not your turn'}
        
        # 2. Get Card
        try:
            player = self.game.players[player_index]
            if not (0 <= card_idx < len(player.hand)):
                return {'success': False, 'error': 'Invalid card index'}
            card = player.hand[card_idx]
        except Exception as e:
             return {'success': False, 'error': str(e)}

        # 3. Check Qayd/Valid Move
        # This logic is heavy. We use TrickManager for validation.
        is_valid, reason = self.game.trick_manager.is_valid_move(
            card, 
            player.hand, 
            player_index
        )
        
        if not is_valid:
            # Check for Qayd trigger (Sherlock) if enabled...
            # For now, just return error
            return {'success': False, 'error': f"Invalid move: {reason}", 'code': 'INVALID_MOVE'}

        # 4. Execute Play
        # Remove card, add to table, log it
        played_card = player.hand.pop(card_idx)
        self.game.table_cards.append({
            'playerId': player.hand_id, # Frontend uses generic ID
            'card': played_card,
            'playedBy': player_index
        })
        
        self.game.history.append({
             'action': 'play_card',
             'player': player_index,
             'card': played_card.to_dict(),
             'trick_number': self.game.trick_manager.current_trick_number
        })
        
        # 5. Notify TrickManager
        self.game.trick_manager.on_card_played(player_index, played_card)
        
        # 6. Check Trick End
        if len(self.game.table_cards) == 4:
            self.game.resolve_trick()
        else:
            # Next player
             self.game.current_player_index = (player_index + 1) % 4
             self.game.reset_timer()
             
        return {'success': True, 'card': played_card, 'table': self.game._get_table_state()}
