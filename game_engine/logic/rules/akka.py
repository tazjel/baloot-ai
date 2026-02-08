from typing import List, Set, Any
from game_engine.models.constants import ORDER_SUN

def check_akka_eligibility(
    hand: List[Any], 
    played_cards: Set[str], 
    trump_suit: str, 
    game_mode: str,
    phase: str
) -> List[str]:
    """
    Pure conditional logic for Akka eligibility.
    
    Args:
        hand: List of Card objects (must have .rank and .suit)
        played_cards: Set of card signatures (e.g. "A♠", "10♥")
        trump_suit: Current trump suit (e.g. 'S', 'H' or 'Sun')
        game_mode: Game mode ('HOKUM', 'SUN')
        phase: Current game phase (e.g. 'PLAYING')

    Returns:
        List of eligible suit symbols (e.g. ['♠', '♦'])
    """
    
    # Rule 1: HOKUM only
    if game_mode != 'HOKUM':
        return []

    # Rule 5: Must be in PLAYING phase
    if phase != 'PLAYING':
        return []

    if not hand:
        return []

    # Non-trump strength order: same as SUN order (7 < 8 < 9 < J < Q < K < 10 < A)
    rank_order = ORDER_SUN  # index = strength; higher index = stronger

    # Group hand by suit
    hand_by_suit = {}
    for c in hand:
        # Assuming c has .suit and .rank attributes
        hand_by_suit.setdefault(c.suit, []).append(c)

    eligible_suits = []

    for suit, cards in hand_by_suit.items():
        # Rule 2: Skip trump suit
        if suit == trump_suit:
            continue

        # Find player's strongest card in this suit
        # We need to handle potential custom Card objects that might compare differently, 
        # but here we rely on rank_order index.
        try:
            my_best = max(cards, key=lambda c: rank_order.index(c.rank))
        except ValueError:
             # If rank is not in ORDER_SUN (shouldn't happen in valid game), skip
             continue

        # Rule 3: Skip Aces (self-evident boss)
        if my_best.rank == 'A':
            continue

        my_strength = rank_order.index(my_best.rank)

        # Check: is any STRONGER card still unplayed (and not in our hand)?
        is_boss = True
        for i in range(my_strength + 1, len(rank_order)):
            higher_rank = rank_order[i]
            card_sig = f"{higher_rank}{suit}"

            if card_sig in played_cards:
                continue  # Already played — no threat

            # Card is unplayed. Do WE hold it?
            we_hold_it = any(c.rank == higher_rank and c.suit == suit for c in hand)
            if we_hold_it:
                # We have a higher card ourselves — so the card we're checking
                # (my_best) is NOT the boss; our higher card is.
                is_boss = False
                break

            # Unplayed AND we don't have it → someone else might → not boss
            is_boss = False
            break

        if is_boss:
            eligible_suits.append(suit)

    return eligible_suits
