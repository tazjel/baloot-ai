from game_engine.models.card import Card
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM, BiddingPhase, BidType
from ai_worker.personality import PersonalityProfile, BALANCED

class BotContext:
    """Typed wrapper for game state to simplify bot logic."""
    def __init__(self, game_state: dict, player_index: int, personality: PersonalityProfile = BALANCED):
        self.raw_state = game_state
        self.player_index = player_index
        self.personality = personality
        
        # Parse Player
        p_data = game_state['players'][player_index]
        self.hand = [Card(c['suit'], c['rank']) for c in p_data['hand']]
        self.position = p_data.get('position', 'Unknown')
        self.name = p_data.get('name', f"Player {player_index}")
        self.team = p_data.get('team', 'Unknown')
        self.avatar = p_data.get('avatar', 'bot_1')

        
        # Parse Game Info
        self.phase = game_state.get('phase')
        self.mode = game_state.get('gameMode')
        self.trump = game_state.get('trumpSuit')
        self.dealer_index = game_state.get('dealerIndex', 0)
        self.bidding_round = game_state.get('biddingRound', 1)
        self.floor_card = None
        if game_state.get('floorCard'):
             fc = game_state['floorCard']
             self.floor_card = Card(fc['suit'], fc['rank'])
             
        # Parse Table
        self.table_cards = []
        for tc in game_state.get('tableCards', []):
             c = tc['card']
             self.table_cards.append({
                  'card': Card(c['suit'], c['rank']),
                  'playedBy': tc['playedBy']
             })
             
        # Derived
        self.is_dealer = (self.player_index == self.dealer_index)
        self.akka_state = game_state.get('akkaState', None)
        
        # Core Components
        from ai_worker.memory import CardMemory
        from ai_worker.mind_client import mind_client
        self.memory = CardMemory()
        self.memory.populate_from_state(self.raw_state)
        self.mind = mind_client # Use singleton
        
        # Play State
        self.played_cards = self.memory.played_cards # Delegate to robust memory
        # ... table_cards parsing remains for immediate context ...
             
        self.lead_suit = None
        self.lead_card = None
        self.winning_card = None
        self.winner_pos = None
        
        if self.table_cards:
             self.lead_card = self.table_cards[0]['card']
             self.lead_suit = self.lead_card.suit
             
             # Determine current winner
             best_idx = 0
             best_card = self.lead_card
             for i, tc in enumerate(self.table_cards):
                  c = tc['card']
                  beats = False
                  # Simple beat check
                  if self.mode == 'HOKUM':
                       if c.suit == self.trump and best_card.suit != self.trump: beats = True
                       elif c.suit == self.trump and best_card.suit == self.trump:
                            beats = self._compare_ranks(c.rank, best_card.rank, 'HOKUM')
                       elif c.suit == self.lead_suit and best_card.suit == self.lead_suit:
                            beats = self._compare_ranks(c.rank, best_card.rank, 'SUN')
                  else: # SUN
                       if c.suit == self.lead_suit:
                            beats = self._compare_ranks(c.rank, best_card.rank, 'SUN')
                            
                  if beats:
                       best_card = c
                       best_idx = i
             
             self.winning_card = best_card
             self.winner_pos = self.table_cards[best_idx]['playedBy']

    @property
    def bidding_phase(self) -> BiddingPhase:
        """Typed accessor for bidding phase."""
        try:
             val = self.raw_state.get('biddingPhase')
             return BiddingPhase(val) if val else None
        except ValueError:
             return None

    @property
    def bid_winner(self):
        """Returns the position of the player who won the bid."""
        return self.raw_state.get('bid', {}).get('bidder')

    def _compare_ranks(self, r1, r2, mode):
        # Return True if r1 > r2
        ord_list = ORDER_HOKUM if mode == 'HOKUM' else ORDER_SUN
        try:
             idx1 = ord_list.index(r1)
             idx2 = ord_list.index(r2)
             return idx1 > idx2
        except ValueError:
             return False

    def is_master_card(self, card):
        # Delegate to memory
        return self.memory.is_master(card.rank, card.suit, self.mode, self.trump)
        
    def is_opponent_void(self, suit):
        # Check if ANY opponent is void in this suit?
        # Or check specific players?
        # Usually we want to know if *current winner* is void?
        # Or if *next player* is void (to avoid them cutting)?
        # For simplicity, let's expose specific check.
        return False # Placeholder if needed, but direct memory access preferred

    def is_player_void(self, position, suit):
        """Checks if a player is known to be void in a suit based on memory."""
        # Map Position Name (Bottom) to Index (for memory lookups if needed)
        # But memory stores by Position Name/Ref?
        # populate_from_state handles this.
        return self.memory.is_void(position, suit)
        
    def get_legal_moves(self):
        """
        Returns a list of indices of legal cards to play from hand.
        Uses shared validation logic.
        """
        from game_engine.logic.validation import is_move_legal
        
        legal_indices = []
        players_team_map = {p['position']: p['team'] for p in self.raw_state['players']}
        table_cards = self.raw_state.get('tableCards', [])
        
        # Parse table cards to match what validator expects (dicts of Card/playedBy)
        # Assuming raw_state tableCards are already dicts with 'card' as dict?
        # Validator expects 'card' to be Card OBJECT.
        # We need to convert them.
        
        # Convert table cards to objects for validation
        real_table_cards = []
        for tc in table_cards:
             c_dict = tc['card']
             c_obj = Card(c_dict['suit'], c_dict['rank'])
             real_table_cards.append({'card': c_obj, 'playedBy': tc['playedBy']})
             
        contract_variant = None
        bid = self.raw_state.get('bid', {})
        # Assuming 'variant' is in bid? Or do we need to check strict structure?
        # Usually bid is just {type: 'HOKUM', suit...}
        # If 'variant' key exists (for Magfool), use it.
        # Currently the game state might not expose variant directly in simple bid dict?
        # But let's assume standard closed/open if HOKUM.
        
        # If not present, assume OPEN for now unless we can find it.
        # Actually, bidding_engine.contract has variant.
        # raw_state might need to be enriched if missing.
        
        for i, card in enumerate(self.hand):
             is_legal = is_move_legal(
                 card=card,
                 hand=self.hand,
                 table_cards=real_table_cards,
                 game_mode=self.mode, # Corrected from self.game_mode
                 trump_suit=self.trump, # Corrected from self.trump_suit
                 my_team=self.team,
                 players_team_map=players_team_map,
                 contract_variant=bid.get('variant') # Pass variant if available
             )
             if is_legal:
                  legal_indices.append(i)
                  
                  
        return legal_indices

    def guess_hands(self):
        """
        Uses the MindReader AI to predict opponent hands based on game history.
        Returns: { player_id: { card_idx: probability } }
        """
        if self.mind and self.mind.active:
             return self.mind.infer_hands(self.raw_state)
        return None
