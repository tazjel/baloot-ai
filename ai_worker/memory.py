import logging

logger = logging.getLogger(__name__)

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']

class CardMemory:
    def __init__(self):
        self.reset()

    def is_card_played(self, rank, suit):
        return f"{rank}{suit}" in self.played_cards

    def get_remaining_cards(self):
        remaining = []
        for s in SUITS:
            for r in RANKS:
                c_str = f"{r}{s}"
                if c_str not in self.played_cards:
                    remaining.append({'rank': r, 'suit': s})
        return remaining

    def get_remaining_in_suit(self, suit):
        return [c for c in self.get_remaining_cards() if c['suit'] == suit]

    def reset(self):
        self.played_cards = set()
        self.voids = {} # Player Ref -> Set of Suits
        self.discards = {} # Player Ref -> List of Discard Events
        self.partners_aces = set() 
        self.turn_history = [] 
        # Proof-Based Qayd: Track suspected crimes until proof is found
        self.suspected_crimes = [] 
        
        # BAYESIAN VOID TRACKING: Probabilistic suit estimation per player
        # {player_pos: {suit: probability_0_to_1}}
        self.suit_probability = {}
        # Track cards remaining per player for precise endgame counting
        self.cards_remaining = {}  # {player_pos: int}
        # Track cards played per suit per player for probability updates
        self.suit_play_count = {}  # {player_pos: {suit: int}}

    def mark_played(self, card_str):
        self.played_cards.add(card_str)

    def populate_from_state(self, game_state):
        """
        Rebuilds memory from the full game history provided in the state.
        Critically, this infers VOIDS based on player actions.
        
        TODO: Upgrade to "Mind's Eye" Probabilistic Memory.
        Current implementation uses binary voids (Has Suit / Void).
        Future: self.hand_distributions = {player: {suit: prob}}
        """
        self.reset()
        
        # 1. Mark Table Cards as Played
        for tc in game_state.get('tableCards', []):
             c = tc['card']
             self.mark_played(f"{c['rank']}{c['suit']}")
             
        # 2. Process Round History (Tricks)
        # Assuming round_history / currentRoundTricks structure:
        # [{'winner': 'Bottom', 'cards': [{'suit': 'S', 'rank': 'A', 'playedBy': 'Bottom'}, ...]}, ...]
        
        history = game_state.get('currentRoundTricks', [])
        # Also check 'pastRoundResults' for previous rounds if we wanted long-term memory?
        # No, Baloot memory is per-round (cards are reshuffled).
        
        trump = game_state.get('trumpSuit')
        mode = game_state.get('gameMode')
        
        for trick in history:
            led_suit = None
            if trick.get('cards'):
                 # Need to handle if cards are objects or dicts
                 first_card = trick['cards'][0]
                 # first_card might be wrapper dict {card: {suit, rank}, playedBy: ...} or just {suit, rank}
                 # Standardize access
                 c_dict = first_card if 'rank' in first_card else first_card.get('card', {})
                 led_suit = c_dict.get('suit')
                 
            involved_players = trick.get('playedBy', []) # Parallel list
                 
            for i, c_data in enumerate(trick.get('cards', [])):
                 # Normalize card data
                 c_inner = c_data if 'rank' in c_data else c_data.get('card', {})
                 rank = c_inner.get('rank')
                 suit = c_inner.get('suit')
                 
                 # Robust Player Position Extraction
                 player_pos = c_data.get('playedBy')
                 if not player_pos and i < len(involved_players):
                      player_pos = involved_players[i]
                 
                 if not player_pos or not rank or not suit:
                      continue

                 # Mark Played
                 self.mark_played(f"{rank}{suit}")
                 
                 # PROOF-BASED QAYD: Check if this play proves a suspected crime
                 # If player is playing a suit they previously claimed void in -> PROOF!
                 trick_idx = history.index(trick)
                 proven_crime = self.check_for_proof(player_pos, suit, trick_idx)
                 if proven_crime:
                      # Store the proof card
                      proven_crime['proof_card'] = {'rank': rank, 'suit': suit}
                 
                 # Infer Voids
                 if led_suit and suit != led_suit:
                      # Player failed to follow suit -> VOID in led_suit
                      self.mark_void(player_pos, led_suit)
                      logger.info(f"[MEMORY] Inferring VOID: Player {player_pos} has no {led_suit} (Played {suit} on {led_suit})")
                      
                      # Track Discard for Signaling History
                      if player_pos not in self.discards: self.discards[player_pos] = []
                      self.discards[player_pos].append({
                          'rank': rank,
                          'suit': suit,
                          'trick_idx': history.index(trick)
                      })
                      
                      # PROOF-BASED QAYD: Record suspected crime
                      # The crime card is what they played (wrong suit)
                      # The void_suit is the suit they claimed not to have
                      self.record_suspected_crime(
                          player_pos=player_pos,
                          trick_idx=history.index(trick),
                          crime_card={'rank': rank, 'suit': suit},
                          void_suit=led_suit
                      )
                      
                      if mode == 'HOKUM' and led_suit != trump and suit != trump:
                           self.mark_void(player_pos, trump)
                           logger.info(f"[MEMORY] Inferring VOID: Player {player_pos} has no {trump} (Failed to cut {led_suit})")

        # BAYESIAN UPDATE: Build probabilistic suit distributions
        self._update_bayesian_probabilities(game_state)

    def mark_void(self, player_ref, suit):
        # player_ref can be int index or string position
        if suit in SUITS:
            self.voids.setdefault(player_ref, set()).add(suit)

    def is_void(self, player_ref, suit):
        return suit in self.voids.get(player_ref, set())

    def get_remaining_trumps(self, trump_suit):
        return [c for c in self.get_remaining_in_suit(trump_suit)]

    def check_contradiction(self, player_ref, card_obj):
        """
        Sherlock's Magnifying Glass:
        Checks if playing 'card_obj' contradicts previously known voids.
        Returns a Reason string if contradictory, else None.
        """
        suit = card_obj.suit
        if self.is_void(player_ref, suit):
             return f"Player {player_ref} played {suit} but previously showed VOID in {suit}."
        return None

    # ========= PROOF-BASED QAYD METHODS =========
    
    def record_suspected_crime(self, player_pos, trick_idx, crime_card, void_suit):
        """
        Record a suspected revoke (player claimed void but might have lied).
        This is tracked until proof is found.
        """
        suspect = {
            'player': player_pos,
            'trick_idx': trick_idx,
            'crime_card': crime_card,  # The card they played (wrong suit)
            'void_suit': void_suit,     # The suit they claimed not to have
            'proven': False,
            'proof_card': None,
            'proof_trick_idx': None
        }
        self.suspected_crimes.append(suspect)
        logger.info(f"[SHERLOCK] Recorded suspected crime: {player_pos} may have revoked on {void_suit} (played {crime_card})")
        
    def check_for_proof(self, player_pos, played_card_suit, current_trick_idx):
        """
        Check if a player just revealed proof of a previous crime.
        If player previously claimed void in a suit, and now plays that suit -> PROOF FOUND!
        Returns the proven crime dict or None.
        """
        for suspect in self.suspected_crimes:
            if suspect['player'] == player_pos and suspect['void_suit'] == played_card_suit and not suspect['proven']:
                # PROOF FOUND!
                suspect['proven'] = True
                suspect['proof_trick_idx'] = current_trick_idx
                logger.info(f"[SHERLOCK] PROOF FOUND! {player_pos} played {played_card_suit} but claimed void in trick {suspect['trick_idx']}")
                return suspect
        return None
    
    def get_proven_crimes(self):
        """Get all crimes that have been proven (have both crime card and proof card)."""
        return [s for s in self.suspected_crimes if s['proven']]
    
    def get_unproven_suspects(self):
        """Get suspected crimes that haven't been proven yet."""
        return [s for s in self.suspected_crimes if not s['proven']]

    # ========= BAYESIAN VOID TRACKING =========

    def _update_bayesian_probabilities(self, game_state):
        """
        Build probabilistic suit distributions for each player.
        Uses remaining cards + known voids to estimate likely holdings.
        """
        positions = ['Bottom', 'Right', 'Top', 'Left']
        tricks_history = game_state.get('currentRoundTricks', [])
        table_cards = game_state.get('tableCards', [])
        total_tricks = len(tricks_history)

        # Count remaining cards per player
        for pos in positions:
            cards_left = 8 - total_tricks
            # Subtract cards played in current trick
            for tc in table_cards:
                if tc.get('playedBy') == pos:
                    cards_left -= 1
            self.cards_remaining[pos] = max(0, cards_left)

        # Count remaining unplayed cards per suit
        remaining_per_suit = {}
        for s in SUITS:
            remaining_per_suit[s] = len(self.get_remaining_in_suit(s))

        total_remaining = sum(remaining_per_suit.values())
        if total_remaining == 0:
            return

        # Calculate probabilities for each player
        for pos in positions:
            if pos not in self.suit_probability:
                self.suit_probability[pos] = {}
            
            player_cards = self.cards_remaining.get(pos, 0)
            if player_cards == 0:
                # No cards left — zero probability for everything
                for s in SUITS:
                    self.suit_probability[pos][s] = 0.0
                continue

            for s in SUITS:
                if self.is_void(pos, s):
                    # Known void — probability is 0
                    self.suit_probability[pos][s] = 0.0
                else:
                    # Estimate probability based on remaining cards
                    # P(has suit) ≈ remaining_in_suit / total_remaining * player_cards
                    if remaining_per_suit[s] > 0 and total_remaining > 0:
                        # Bayesian estimate: given N remaining cards dealt to ~3 players,
                        # probability at least 1 of their cards is this suit
                        prob = 1.0 - ((1.0 - remaining_per_suit[s] / total_remaining) ** player_cards)
                        self.suit_probability[pos][s] = min(1.0, prob)
                    else:
                        self.suit_probability[pos][s] = 0.0

    def get_suit_probability(self, player_pos, suit):
        """Get estimated probability that a player holds at least one card of a suit."""
        return self.suit_probability.get(player_pos, {}).get(suit, 0.5)

    def get_likely_holdings(self, player_pos, threshold=0.3):
        """Get suits a player likely still holds (probability > threshold)."""
        probs = self.suit_probability.get(player_pos, {})
        return {s: p for s, p in probs.items() if p > threshold}

    def is_master(self, rank, suit, mode, trump):
        """
        Check if a card is the highest remaining in its suit.
        """
        remaining = self.get_remaining_in_suit(suit)
        if not remaining: return True 
        
        order = []
        if mode == 'HOKUM':
            if suit == trump:
                order = ['J', '9', 'A', '10', 'K', 'Q', '8', '7']
            else:
                order = ['A', 'K', 'Q', 'J', '10', '9', '8', '7']
        else: # SUN
             order = ['A', '10', 'K', 'Q', 'J', '9', '8', '7']
             
        my_idx = -1
        try:
            my_idx = order.index(rank)
        except ValueError:
            return False 
            
        for c in remaining:
            if c['rank'] == rank: continue 
            try:
                op_idx = order.index(c['rank'])
                if op_idx < my_idx:
                    return False # Found a stronger card
            except ValueError:
                continue

        return True
