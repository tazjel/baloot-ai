import logging
import time
from typing import Dict, Optional, Any

from game_engine.models.constants import GamePhase

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
        if player_index != self.game.current_turn:
             return {'success': False, 'error': 'Not your turn'}
        
        # 2. Get Card
        try:
            player = self.game.players[player_index]
            if not (0 <= card_idx < len(player.hand)):
                return {'success': False, 'error': 'Invalid card index'}
            card = player.hand[card_idx]
        except Exception as e:
             return {'success': False, 'error': str(e)}

        # 3. Check Valid Move
        is_legal = self.game.trick_manager.is_valid_move(card, player.hand)
        
        # 4. Handle Illegal Moves (Strict vs Permissive)
        if not is_legal:
            if self.game.strictMode:
                 return {'success': False, 'error': 'Invalid move (Strict Mode)', 'code': 'INVALID_MOVE'}
            else:
                 # Flag as illegal but proceed (for Qayd)
                 logger.warning(f"Player {player_index} played ILLEGAL card: {card}")
                 if not metadata: metadata = {}
                 metadata['is_illegal'] = True
                 metadata['illegal_reason'] = 'Rule Violation' # capture details if possible

        # 5. Execute Play
        played_card = player.hand.pop(card_idx)
        
        # Ensure metadata has cardId if provided (for frontend tracking)
        if metadata is None: metadata = {}
        
        self.game.table_cards.append({
            'playerId': player.id, 
            'card': played_card,
            'playedBy': player.position,
            'metadata': metadata
        })
        
        # 6. Notify TrickManager / Resolve Trick
        if len(self.game.table_cards) == 4:
            self.game.resolve_trick()
        else:
            # Next player
            self.game.current_turn = (player_index + 1) % 4
            self.game.reset_timer()
             
        return {'success': True, 'card': played_card.to_dict(), 'table': [tc['card'].to_dict() for tc in self.game.table_cards]}

