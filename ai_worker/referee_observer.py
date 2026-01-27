import logging
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM

logger = logging.getLogger(__name__)

class RefereeObserver:
    """
    Enforces rules and handles mandatory responses (Sawa, Qayd).
    """

    def check_qayd(self, ctx, game_state):
        """
        Check if the last move was illegal and claim Qayd if so.
        """
        if ctx.phase == 'PLAYING' and ctx.table_cards:
            last_play_raw = game_state.get('tableCards', [])[-1]
            if 'metadata' in last_play_raw and last_play_raw.get('metadata', {}).get('is_illegal'):
                logger.info(f"[REFEREE] {ctx.position} detected illegal move! Calling Qayd.")
                return {
                    "action": "QAYD_CLAIM",
                    "reasoning": "Opponent played an illegal move (Flagged)."
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
