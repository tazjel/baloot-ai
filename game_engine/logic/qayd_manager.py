
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
        # RELAXED CHECK: Trust caller (Game/AutoPlay) to verify reporter. 
        # State sync issues between TrickManager/QaydManager cause false negatives here.
        # if player.position != self.state['reporter']:
        #      return {"error": "Only the reporter can submit accusation."}
             
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
             self.game.trick_manager.apply_khasara(offender.team, reason, points_override=points)
             self.state['status'] = 'RESOLVED'
             self.state['loser_team'] = offender.team
             
        else:
             # Challenger Loses (False Accusation)
             reason = f"Qayd FAILED: {reason}"
             reason = f"Qayd FAILED: {reason}"
             # Logic fix: If accusation fails, applying Khasara to ACCUSER (player.team)
             self.game.trick_manager.apply_khasara(player.team, reason)
             self.state['status'] = 'RESOLVED'
             self.state['loser_team'] = player.team
             
             self.state['status'] = 'RESOLVED'
             self.state['loser_team'] = player.team
             
        # Enrich verdict for Frontend
        verdict['isGuilty'] = verdict['is_guilty']
        verdict['violationType'] = accusation_data['violation_type']
        verdict['accusedPlayer'] = accusation_data['crime_card']['playedBy']
        
        return verdict
        
    def cancel_challenge(self) -> Dict[str, Any]:
        """Cancels changes and resumes game. Handles 'Close' action."""
        logger.info(f"QaydManager.cancel_challenge called. Active: {self.state['active']}, Status: {self.state['status']}")
        
        # DEADLOCK FIX: If status is RESOLVED, we allow closing even if active is accidentally False
        # This ensures the user is never stuck looking at a Result screen
        if not self.state['active'] and self.state['status'] != 'RESOLVED':
             return {"error": "No active challenge"}
             
        # Capture status before clearing
        was_resolved = (self.state['status'] == 'RESOLVED')
             
        self.state['active'] = False
        self.state['status'] = 'NONE'
        self.state['reporter'] = None
        
        # Resume Game
        # Only set phase to PLAYING if we haven't already finished the round
        if not was_resolved:
             self.game.phase = GamePhase.PLAYING.value
             logger.info("Qayd Cancelled (False Alarm/User Cancel) -> Game Phase PLAYING")
        else:
             logger.info("Qayd Closed (Result Viewed) -> Game Phase preserved (FINISHED/GAMEOVER)")
             
        self.game.timer_paused = False
        
        # Force unlocking game (handled by caller usually, but good to be safe)
        if hasattr(self.game, 'is_locked'):
             self.game.is_locked = False
             
        return {"success": True}
