import logging
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM

logger = logging.getLogger(__name__)

class RefereeObserver:
    """
    Enforces rules and handles mandatory responses (Sawa, Qayd).
    """

    def check_qayd(self, ctx, game_state, memory=None):
        """
        PROOF-BASED QAYD DETECTION (Kammelna-style)
        
        Instead of triggering immediately on 'is_illegal' flag,
        we wait for PROOF: when the cheater later plays a card of the
        suit they previously claimed not to have.
        
        Args:
            ctx: Bot context with position, hand, etc.
            memory: CardMemory instance for tracking suspected crimes
            
        Returns:
            dict with 'action': 'QAYD_ACCUSATION' if proven crime found, else None
        """
        if ctx.phase != 'PLAYING' or not memory:
            return None
            
        # Check if memory has any proven crimes from opponents
        proven_crimes = memory.get_proven_crimes()
        
        for crime in proven_crimes:
            offender_pos = crime['player']
            
            # Only accuse opponents (not teammate)
            my_team = 'us' if ctx.position in ['Bottom', 'Top'] else 'them'
            offender_team = 'us' if offender_pos in ['Bottom', 'Top'] else 'them'
            
            if my_team != offender_team:
                # Found a proven crime by opponent!
                logger.info(f"[SHERLOCK] {ctx.position} found PROVEN crime by {offender_pos}: revoked on {crime['void_suit']}")
                
                return {
                    "action": "QAYD_ACCUSATION",
                    "qayd_type": "REVOKE",  # قاطع
                    "crime": {
                        "player": offender_pos,
                        "crime_card": crime['crime_card'],
                        "crime_trick_idx": crime['trick_idx'],
                        "proof_card": crime.get('proof_card'),
                        "proof_trick_idx": crime.get('proof_trick_idx'),
                        "void_suit": crime['void_suit']
                    },
                    "reasoning": f"{offender_pos} revoked on {crime['void_suit']} in trick {crime['trick_idx']}, proven in trick {crime.get('proof_trick_idx')}"
                }
        
        return None

    def check_sawa(self, ctx, game_state):
        """
        DEPRECATED: Sawa is now server-validated.
        The old ACCEPT/REFUSE opponent response model has been removed.
        handle_sawa() in trick_manager validates eligibility and resolves instantly.
        This stub remains to prevent import errors from agent.py.
        """
        return None
