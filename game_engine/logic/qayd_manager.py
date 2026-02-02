
import time
import logging
from typing import Dict, Any, Optional

from game_engine.models.constants import GamePhase
from server.logging_utils import log_event, logger

# Avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game_engine.logic.game import Game

class QaydManager:
    def __init__(self, game: 'Game'):
        self.game = game
        self.state = {
            'active': False,
            'reporter': None,
            'reason': None,
            'status': 'NONE', # NONE, INVESTIGATING, REVIEW, RESOLVED
            'target_play': None,
            'verdict_message': None,
            'crime_card_index': -1,
            'proof_card_index': -1,
            'loser_team': None,
            'penalty_points': 0
        }

    def reset(self):
        """Reset state for new round"""
        self.state = {
            'active': False,
            'reporter': None,
            'reason': None,
            'status': 'NONE',
            'target_play': None,
            'verdict_message': None,
            'crime_card_index': -1,
            'proof_card_index': -1,
            'loser_team': None,
            'penalty_points': 0
        }

    def initiate_challenge(self, player_index: int) -> Dict[str, Any]:
        """
        Starts a Forensic Challenge (Qayd).
        Pauses the game and sets state to CHALLENGE.
        """
        if self.game.phase != GamePhase.PLAYING.value:
             return {"error": "Can only challenge during Playing phase."}
        
        if self.state.get('active'):
             return {"error": "Challenge already active."}
             
        self.game.phase = GamePhase.CHALLENGE.value
        self.game.pause_timer()
        
        player = self.game.players[player_index]
        self.state['active'] = True
        self.state['reporter'] = player.position
        self.state['status'] = 'INVESTIGATING'
        self.state['reason'] = None
        
        log_event("CHALLENGE_STARTED", self.game.room_id, details={'reporter': player.position})
        return {"success": True}

    def process_accusation(self, player_index: int, accusation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates the accusation using ForensicReferee.
        """
        if self.game.phase != GamePhase.CHALLENGE.value:
             return {"error": "Not in Challenge phase."}
             
        player = self.game.players[player_index]
        if player.position != self.state['reporter']:
             return {"error": "Only the reporter can submit accusation."}
             
        from game_engine.logic.forensic import ForensicReferee
        
        gameState = self.game.get_game_state()
        
        # Call Referee
        verdict = ForensicReferee.validate_accusation(
             game_snapshot=gameState,
             crime_card=accusation_data['crime_card'],
             proof_card=accusation_data['proof_card'],
             violation_type=accusation_data['violation_type']
        )
        
        logger.info(f"FORENSIC VERDICT: {verdict}")
        
        reason = verdict['reason']
        self.state['verdict_message'] = reason
        
        if verdict['is_guilty']:
             # Offender Loses
             offender_pos = accusation_data['crime_card']['playedBy']
             offender = next(p for p in self.game.players if p.position == offender_pos)
             
             reason = f"Qayd PROVEN: {reason}"
             
             # Apply Khasara to Offender Team
             points = verdict.get('penalty_score')
             self.game.apply_khasara(offender.team, reason, points_override=points)
             self.state['status'] = 'RESOLVED'
             self.state['loser_team'] = offender.team
             
        else:
             # Challenger Loses (False Accusation)
             reason = f"Qayd FAILED: {reason}"
             self.game.apply_khasara(player.team, reason)
             self.state['status'] = 'RESOLVED'
             self.state['loser_team'] = player.team
             
        return verdict
        
    def cancel_challenge(self) -> Dict[str, Any]:
        """Cancels changes and resumes game"""
        if not self.state['active']:
             return {"error": "No active challenge"}
             
        self.state['active'] = False
        self.state['status'] = 'NONE'
        self.state['reporter'] = None
        
        # Resume Game
        self.game.phase = GamePhase.PLAYING.value
        self.game.timer_paused = False
        return {"success": True}
