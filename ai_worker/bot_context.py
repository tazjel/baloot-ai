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
        
        # Play State
        self.played_cards = set()
        # From Round History
        for t in game_state.get('currentRoundTricks', []):
             for c in t.get('cards', []):
                  self.played_cards.add(f"{c['rank']}{c['suit']}")
        # From Table
        for tc in self.table_cards:
             c = tc['card']
             self.played_cards.add(f"{c.rank}{c.suit}")
             
        self.lead_suit = None
        self.lead_card = None
        self.winning_card = None
        self.winner_pos = None
        
        if self.table_cards:
             self.lead_card = self.table_cards[0]['card']
             self.lead_suit = self.lead_card.suit
             
             self.lead_suit = self.lead_card.suit
             
             # Determine current winner
             best_idx = 0
             best_card = self.lead_card
             for i, tc in enumerate(self.table_cards):
                  c = tc['card']
                  beats = False
                  # Simple beat check (Refactor to use centralized logic later)
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
             # Default to ROUND_1 if missing, or handle gracefully
             val = self.raw_state.get('biddingPhase')
             return BiddingPhase(val) if val else None
        except ValueError:
             return None

    def _compare_ranks(self, r1, r2, mode):
        # Return True if r1 > r2
        ord_list = ORDER_HOKUM if mode == 'HOKUM' else ORDER_SUN
        # Safely handle missing ranks if needed
        try:
             idx1 = ord_list.index(r1)
             idx2 = ord_list.index(r2)
             return idx1 > idx2
        except ValueError:
             return False

    def is_master_card(self, card):
        # Check if this card is the highest remaining of its suit
        # Ranks higher than card.rank must be in self.played_cards
        ord_list = ORDER_HOKUM if self.mode == 'HOKUM' and card.suit == self.trump else ORDER_SUN
        
        try:
             my_rank_idx = ord_list.index(card.rank)
             # Higher ranks are at HIGHER indices in standard lists
             higher_ranks = ord_list[my_rank_idx+1:]
             
             for h_rank in higher_ranks:
                  # Check if UNPLAYED
                  # If a higher card is NOT played, then I am NOT master.
                  # Note: self.played_cards stores "RankSuit" e.g. "A♥"
                  code = f"{h_rank}{card.suit}"
                  if code not in self.played_cards:
                       # Also check: Is it in MY hand?
                       # If I hold the higher card, handled separately?
                       # Usually is_master called on a card I define.
                       # If I have A and K, and ask is_master(K):
                       # Higher is A. A is not played. So K is NOT master. Correct.
                       return False
             return True
        except ValueError:
             return False
