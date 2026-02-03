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
        Check if a Sawa claim is pending and generate a response.
        """
        sawa_state = game_state.get('sawaState') or game_state.get('sawa_state')
        
        # Validate Sawa State
        if not sawa_state or not sawa_state.get('active') or sawa_state.get('status') != 'PENDING':
            return None

        claimer_pos = sawa_state['claimer']
        my_pos = ctx.position
        
        # Check Teams
        my_team = 'us' if my_pos in ['Bottom', 'Top'] else 'them'
        claimer_team = 'us' if claimer_pos in ['Bottom', 'Top'] else 'them'
        
        # Only opponents respond
        if my_team == claimer_team:
            return None

        # Check if already responded
        if my_pos in sawa_state.get('responses', {}):
            return None

        # Calculate Response
        response_data = self._evaluate_sawa_refusal(ctx)
        logger.info(f"[REFEREE] Responding to Sawa from {claimer_pos} with {response_data['response']}")
        
        return {
            "action": "SAWA_RESPONSE", 
            "response": response_data['response'], 
            "reasoning": response_data['reasoning']
        }

    def _evaluate_sawa_refusal(self, ctx):
        """
        Evaluate if we have a Master Card to refuse Sawa.
        """
        refusal_card = None
        
        for i, c in enumerate(ctx.hand):
             # Is this card a Master?
             if ctx.is_master_card(c):
                  # Logic for HOKUM Trumps vs Non-Trumps
                  if ctx.mode == 'HOKUM':
                       # Safe Strategy: Refuse if I can potentially win a trick
                       refusal_card = c
                       break
                  else:
                       # SUN Mode -> Any master wins.
                       refusal_card = c
                       break
                       
        if refusal_card:
             return {"response": "REFUSE", "reasoning": f"I hold Master Card: {refusal_card}"}
        else:
             return {"response": "ACCEPT", "reasoning": "No guaranteed winning cards"}
