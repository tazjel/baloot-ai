import random
from typing import List, Set
from game_engine.models.card import Card
from ai_worker.bot_context import BotContext
from game_engine.models.constants import SUITS

def generate_random_distribution(ctx: BotContext) -> List[List[Card]]:
    """
    Generates a random distribution of remaining cards to other players,
    respecting known voids and played cards.
    Returns list of 4 Hands (indices 0..3).
    """
    # 1. Identify Remaining Cards
    # We need a full deck set
    all_cards = []
    for s in SUITS:
        ranks = ['7','8','9','10','J','Q','K','A']
        for r in ranks:
            all_cards.append(Card(s, r))
            
    # Remove My Hand
    # Defensive: Ensure ctx.hand contains Card objects
    sanitized_hand = []
    for c in ctx.hand:
        if isinstance(c, dict):
            # Reconstruct Card from dict if needed
            sanitized_hand.append(Card(c['suit'], c['rank']))
        elif hasattr(c, 'suit'):
             sanitized_hand.append(c)
        else:
             # Fallback or error?
             pass
             
    my_hand_str = [str(c) for c in sanitized_hand]
    
    # Remove Played Cards (from Memory)
    played = ctx.memory.played_cards # Set of strings like "7H"

        
    remaining = []
    for c in all_cards:
        if str(c) not in my_hand_str and str(c) not in played:
            remaining.append(c)
            
    # 2. Identify Player Current Counts
    # We need to know how many cards each opponent SHOULD have.
    # Total cards = 32. 4 players. 8 each.
    # Round number? 
    # Current trick size tells us who played.
    
    tricks_history = ctx.raw_state.get('currentRoundTricks', [])
    current_trick_size = len(ctx.raw_state.get('tableCards', []))
    
    # Ideally, track cards per player.
    # Simplified: Assume all start with 8. Subtract plays.
    
    # 3. Allocator
    # Shuffle remaining
    random.shuffle(remaining)
    
    # Distribute (Blindly for now - ignoring voids logic for MVP)
    # Map to positions
    hands = [[], [], [], []] # Bottom, Right, Top, Left
    
    # Fill Bottom (Self)
    hands[0] = [c for c in sanitized_hand] # Copy
    
    # Fill Others — use precise card counts from Memory (Bayesian tracking)
    positions = ['Bottom', 'Right', 'Top', 'Left']
    target_counts = {}

    if ctx.memory.cards_remaining:
        # Memory already tracks precise counts (accounts for tricks + current table)
        for i, pos in enumerate(positions):
            target_counts[i] = ctx.memory.cards_remaining.get(pos, 0)
    else:
        # Fallback: compute manually if memory wasn't populated
        played_in_current = [p['playedBy'] for p in ctx.raw_state.get('tableCards', [])]
        total_tricks = len(tricks_history)
        for i, pos in enumerate(positions):
            cards_left = 8 - total_tricks
            if pos in played_in_current:
                cards_left -= 1
            target_counts[i] = cards_left
        
    # --- CONSTRAINT-BASED DISTRIBUTION ---
    # We have 'remaining' cards and 'target_counts' per player.
    # We have 'ctx.memory.voids' (Map: pos_string -> Set[suits]).
    
    player_positions = ['Bottom', 'Right', 'Top', 'Left']
    
    # Filter valid slots for each card
    # Simplest approach: Shuffle cards, try to assign to valid player with space. If stuck, restart.
    
    max_attempts = 10
    success = False
    
    for attempt in range(max_attempts):
         random.shuffle(remaining)
         
         # Reset Hands (Keep Bottom fixed)
         temp_hands = [[], [], [], []]
         temp_hands[0] = [c for c in ctx.hand]
         
         current_counts = {i: 0 for i in range(4)}
         
         # Identify who needs cards
         needs_cards = [] # List of player_idx
         for i in range(1, 4): # Right, Top, Left
              count_needed = target_counts[i]
              for _ in range(count_needed):
                   needs_cards.append(i)
         
         # Optimize: needs_cards list is what we iterate? 
         # No, iterate CARDS and find home.
         
         fail_attempt = False
         
         # Count check
         if len(needs_cards) != len(remaining):
              # Mismatch in tracking (e.g. played cards not synced)
              # Just force fill to avoid crash
              pass
              
         # To simplify: We cycle through players and give cards, checking constraints.
         # But specific players might be constrained on specific suits.
         # Hard constraints first?
         
         # Let's map Card -> [Valid Players]
         card_options = []
         for card in remaining:
              options = []
              for p_idx in range(1, 4): # 1, 2, 3
                   pos_str = player_positions[p_idx]
                   if target_counts[p_idx] > len(temp_hands[p_idx]):
                        # Has room
                        # Check Void
                        is_void = ctx.memory.is_void(pos_str, card.suit)
                        if not is_void:
                             options.append(p_idx)
                             
              if not options:
                   fail_attempt = True
                   break
              card_options.append((card, options))
              
         if fail_attempt: continue
         
         # Distribution (Greedy with some randomness)
         # Sort by "Most Constrained" (Fewest Options) first to avoid getting stuck?
         card_options.sort(key=lambda x: len(x[1]))
         
         for card, options in card_options:
               # Filter options to those who STILL have room
               valid_opts = [idx for idx in options if len(temp_hands[idx]) < target_counts[idx]]
               
               if not valid_opts:
                    fail_attempt = True
                    break
               
               # BAYESIAN WEIGHTING: Prefer assigning cards to players
               # who are more likely to hold that suit
               if len(valid_opts) > 1 and hasattr(ctx.memory, 'suit_probability') and ctx.memory.suit_probability:
                    weights = []
                    for idx in valid_opts:
                        pos = player_positions[idx]
                        prob = ctx.memory.get_suit_probability(pos, card.suit)
                        weights.append(max(0.1, prob))  # Floor at 0.1 to avoid zero-weight
                    total_w = sum(weights)
                    if total_w > 0:
                        weights = [w / total_w for w in weights]
                        chosen_idx = random.choices(valid_opts, weights=weights, k=1)[0]
                    else:
                        chosen_idx = random.choice(valid_opts)
               else:
                    chosen_idx = random.choice(valid_opts)
               temp_hands[chosen_idx].append(card)
              
         if not fail_attempt:
              hands = temp_hands
              success = True
              break
              
    if not success:
         # Fallback to naive distribution (Constraint Violation is better than Crash)
         # Re-run strict naive
         return _naive_distribution(remaining, target_counts, ctx.hand)
         
    return hands

def _naive_distribution(remaining, target_counts, my_hand):
    hands = [[], [], [], []]
    
    # Defensive: Ensure my_hand contains Card objects even here (if passed directly)
    sanitized_my_hand = []
    for c in my_hand:
        if isinstance(c, dict):
            sanitized_my_hand.append(Card(c['suit'], c['rank']))
        elif hasattr(c, 'suit'):
             sanitized_my_hand.append(c)
             
    hands[0] = [c for c in sanitized_my_hand]
    
    current_idx_for_dist = 1
    for card in remaining:
        while current_idx_for_dist < 4 and len(hands[current_idx_for_dist]) >= target_counts[current_idx_for_dist]:
             current_idx_for_dist += 1
             
        if current_idx_for_dist < 4:
             hands[current_idx_for_dist].append(card)
    return hands

