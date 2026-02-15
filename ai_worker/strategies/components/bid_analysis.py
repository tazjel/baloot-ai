"""Opponent bid analysis and Gablak window evaluation.

Pure-function module extracted from BiddingStrategy for independent testability.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def analyze_opponent_bids(bid_history: list, my_position: str, partner_position: str) -> dict:
    """Analyze opponent bid history to extract defensive intelligence.

    @param bid_history: List of bid entries from game state.
    @param my_position: My position name (e.g. 'Bottom').
    @param partner_position: Partner position name (e.g. 'Top').
    @returns Dict with keys: opponent_bid_sun, opponent_bid_hokum_suit,
             opponent_passed_r1, partner_bid_and_opp_competed.
    """
    opp_bid_sun = False
    opp_hokum_suit = None
    opp_passes = 0
    opp_count = 0
    partner_bid = False
    opp_bid_after_partner = False

    for entry in bid_history or []:
        player = entry.get('player', entry.get('bidder', ''))
        action = entry.get('action', entry.get('type', 'PASS'))
        suit = entry.get('suit')

        is_opponent = (player != my_position and player != partner_position)
        is_partner = (player == partner_position)

        if is_opponent:
            opp_count += 1
            if action == 'PASS':
                opp_passes += 1
            elif action == 'SUN':
                opp_bid_sun = True
            elif action == 'HOKUM' and suit:
                opp_hokum_suit = suit
            # Check if opponent bid after partner
            if action in ('SUN', 'HOKUM') and partner_bid:
                opp_bid_after_partner = True

        if is_partner and action in ('SUN', 'HOKUM'):
            partner_bid = True

    return {
        'opponent_bid_sun': opp_bid_sun,
        'opponent_bid_hokum_suit': opp_hokum_suit,
        'opponent_passed_r1': opp_count >= 2 and opp_passes >= 2,
        'partner_bid_and_opp_competed': partner_bid and opp_bid_after_partner,
    }


def evaluate_gablak(hand: list, floor_card, bidding_round: int,
                    suits: list, sun_strength_fn, hokum_strength_fn) -> dict:
    """Handle Gablak window — steal bid if we have a strong hand.

    @param hand: Player's current hand (list of Card objects).
    @param floor_card: The floor card (Card or None).
    @param bidding_round: Current bidding round (1 or 2).
    @param suits: List of valid suits to evaluate.
    @param sun_strength_fn: Callable to calculate SUN strength.
    @param hokum_strength_fn: Callable to calculate HOKUM strength.
    @returns Bid action dict with 'action' and 'reasoning' keys.
    """
    sun_score = sun_strength_fn(hand)

    # Steal with Sun if we have a very strong hand
    if sun_score >= 28:
        return {"action": "SUN", "reasoning": f"Gablak Steal: Strong Sun ({sun_score})"}

    # Steal Hokum if we have dominant trump
    for suit in suits:
        if bidding_round == 1 and floor_card and suit != floor_card.suit:
            continue
        if bidding_round == 2 and floor_card and suit == floor_card.suit:
            continue
        fc_for_eval = floor_card if bidding_round == 1 else None
        score = hokum_strength_fn(hand, suit, floor_card=fc_for_eval)
        if score >= 24:
            return {"action": "HOKUM", "suit": suit, "reasoning": f"Gablak Steal: Strong {suit} ({score})"}

    return {"action": "PASS", "reasoning": "Waive Gablak"}
