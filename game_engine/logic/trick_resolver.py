"""
Trick Resolver - Pure Logic for Trick Resolution
================================================

Handles trick winner determination, card strength comparison, and point calculation.
"""

from typing import List, Dict, Tuple, Any
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM, POINT_VALUES_SUN, POINT_VALUES_HOKUM

class TrickResolver:
    """Pure logic class for resolving trick outcomes."""

    @staticmethod
    def get_card_points(card: Card, game_mode: str, trump_suit: str = None) -> int:
        """Return the point value of a card based on current game mode and trump suit."""
        if game_mode == "SUN":
             return POINT_VALUES_SUN[card.rank]
        else:
             if card.suit == trump_suit:
                  return POINT_VALUES_HOKUM[card.rank]
             else:
                  return POINT_VALUES_SUN[card.rank]

    @staticmethod
    def get_trick_winner(table_cards: List[Dict], game_mode: str, trump_suit: str = None) -> int:
        """
        Determine the index (within table_cards) of the trick-winning card.
        table_cards is expected to be a list of dicts with a 'card' key containing a Card object.
        """
        if not table_cards:
            return -1

        lead_card = table_cards[0]['card']
        best_idx = 0
        current_best = -1
        
        for i, play in enumerate(table_cards):
            card = play['card']
            strength = -1
            
            if game_mode == "SUN":
                if card.suit == lead_card.suit:
                    strength = ORDER_SUN.index(card.rank)
            else:
                if card.suit == trump_suit:
                    strength = 100 + ORDER_HOKUM.index(card.rank)
                elif card.suit == lead_card.suit:
                    strength = ORDER_SUN.index(card.rank)
            
            if strength > current_best:
                current_best = strength
                best_idx = i
        return best_idx

    @staticmethod
    def can_beat_trump(winning_card: Card, hand: List[Card], trump_suit: str) -> Tuple[bool, List[Card]]:
        """Check if the hand contains a trump card that can beat the current winner.

        Returns a tuple of (can_beat, list_of_beating_cards).
        """
        if winning_card.suit != trump_suit:
            # Any trump beats a non-trump
            beating_cards = [c for c in hand if c.suit == trump_suit]
            return (len(beating_cards) > 0), beating_cards

        winning_strength = 100 + ORDER_HOKUM.index(winning_card.rank)
        beating_cards = []
        for c in hand:
            if c.suit == trump_suit:
                 s = 100 + ORDER_HOKUM.index(c.rank)
                 if s > winning_strength:
                      beating_cards.append(c)
        return (len(beating_cards) > 0), beating_cards
