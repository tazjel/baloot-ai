from game_engine.models.card import Card
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM, BiddingPhase, BidType
from ai_worker.personality import PersonalityProfile, BALANCED
import functools

class BotContext:
    """Typed wrapper for game state to simplify bot logic."""
    def __init__(self, game_state: dict, player_index: int, personality: PersonalityProfile = BALANCED):
        self.raw_state = game_state
        self.player_index = player_index
        self.personality = personality

        self._parse_player(game_state, player_index)
        self._parse_game_info(game_state)
        self._parse_table(game_state)
        self._build_memory(game_state)

    def _parse_player(self, game_state: dict, player_index: int):
        """Extract player identity, hand, and team from game state."""
        p_data = game_state['players'][player_index]
        self.hand = [Card(c['suit'], c['rank']) for c in p_data['hand']]
        self.position = p_data.get('position', 'Unknown')
        self.name = p_data.get('name', f"Player {player_index}")
        self.team = p_data.get('team', 'Unknown')
        self.avatar = p_data.get('avatar', 'bot_1')

    def _parse_game_info(self, game_state: dict):
        """Extract phase, mode, trump, scores, and derived flags."""
        self.phase = game_state.get('phase')
        self.mode = game_state.get('gameMode')
        self.trump = game_state.get('trumpSuit')
        self.dealer_index = game_state.get('dealerIndex', 0)
        self.bidding_round = game_state.get('biddingRound', 1)
        self.is_dealer = (self.player_index == self.dealer_index)
        self.akka_state = game_state.get('akkaState', None)

        self.floor_card = None
        if game_state.get('floorCard'):
            fc = game_state['floorCard']
            self.floor_card = Card(fc['suit'], fc['rank'])

        # Score-Aware Tactics
        team_scores = game_state.get('teamScores', {'us': 0, 'them': 0})
        match_scores = game_state.get('matchScores', {'us': 0, 'them': 0})
        self.our_score = team_scores.get('us', 0)
        self.their_score = team_scores.get('them', 0)
        self.score_differential = self.our_score - self.their_score
        self.match_differential = match_scores.get('us', 0) - match_scores.get('them', 0)
        self.is_desperate = self.score_differential < -50
        self.is_protecting = self.score_differential > 100

        # Dealer-Position Tactical Awareness (Al-Ta'sheer Protocol)
        # First player = left of dealer = offensive advantage (leads first)
        self.is_first_player = (self.player_index == (self.dealer_index + 1) % 4)
        partner_idx = (self.player_index + 2) % 4
        self.partner_is_first = (partner_idx == (self.dealer_index + 1) % 4)
        self.is_offensive = self.is_first_player or self.partner_is_first

        # Match scores for risk management (doubling danger zone)
        self.match_score_us = match_scores.get('us', 0)
        self.match_score_them = match_scores.get('them', 0)

    def _parse_table(self, game_state: dict):
        """Parse table cards, determine lead suit, and find current trick winner."""
        self.table_cards = []
        for tc in game_state.get('tableCards', []):
            c = tc['card']
            self.table_cards.append({
                'card': Card(c['suit'], c['rank']),
                'playedBy': tc['playedBy']
            })

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
                if self.mode == 'HOKUM':
                    if c.suit == self.trump and best_card.suit != self.trump: beats = True
                    elif c.suit == self.trump and best_card.suit == self.trump:
                        beats = self._compare_ranks(c.rank, best_card.rank, 'HOKUM')
                    elif c.suit == self.lead_suit and best_card.suit == self.lead_suit:
                        beats = self._compare_ranks(c.rank, best_card.rank, 'SUN')
                else:  # SUN
                    if c.suit == self.lead_suit:
                        beats = self._compare_ranks(c.rank, best_card.rank, 'SUN')

                if beats:
                    best_card = c
                    best_idx = i

            self.winning_card = best_card
            self.winner_pos = self.table_cards[best_idx]['playedBy']

    def _build_memory(self, game_state: dict):
        """Initialize card memory, card tracker, and populate from game history."""
        from ai_worker.memory import CardMemory
        from ai_worker.mind_client import mind_client
        from ai_worker.strategies.components.card_tracker import CardTracker
        self.memory = CardMemory()
        self.memory.populate_from_state(self.raw_state)
        self.mind = mind_client
        self.played_cards = self.memory.played_cards

        # Card Tracker — real-time deck tracking with void inference
        raw_history_data = game_state.get('currentRoundTricks', [])
        raw_table = game_state.get('tableCards', [])

        # Normalize: currentRoundTricks can be list-of-dicts (trick objects with 'cards' key)
        # or list-of-lists (already flat play entries). CardTracker expects list[list[dict]].
        normalized_history = []
        for trick in raw_history_data:
            if isinstance(trick, dict):
                # Trick object: extract the 'cards' list
                cards = trick.get('cards', [])
                if cards:
                    normalized_history.append(cards)
            elif isinstance(trick, list):
                # Already a list of play entries
                if trick:
                    normalized_history.append(trick)

        self.tracker = CardTracker(self.hand, normalized_history, raw_table, self.position)

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
        """Check if ANY opponent is known void in *suit* (via CardTracker)."""
        positions = ['Bottom', 'Right', 'Top', 'Left']
        partner_idx = (self.player_index + 2) % 4
        partner_pos = positions[partner_idx]
        void_players = self.tracker.get_void_players(suit)
        return any(p != self.position and p != partner_pos for p in void_players)

    def is_player_void(self, position, suit):
        """Checks if a player is known to be void in a suit based on memory."""
        # Map Position Name (Bottom) to Index (for memory lookups if needed)
        # But memory stores by Position Name/Ref?
        # populate_from_state handles this.
        return self.memory.is_void(position, suit)
        
    @functools.cached_property
    def players_team_map(self) -> dict[str, str]:
        """Performance: Cache team map to avoid repeated list comprehensions in MCTS."""
        return {p['position']: p['team'] for p in self.raw_state['players']}

    def get_legal_moves(self):
        """
        Returns a list of indices of legal cards to play from hand.
        Uses shared validation logic.
        """
        from game_engine.logic.validation import is_move_legal
        
        legal_indices = []
        players_team_map = self.players_team_map
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

    def read_partner_info(self) -> dict | None:
        """Infer partner's likely holdings from bids and trick history.

        Returns a dict with likely_strong_suits, likely_void_suits,
        estimated_trumps, has_high_trumps, confidence, and detail.
        """
        try:
            from ai_worker.strategies.components.partner_read import read_partner
            positions = ['Bottom', 'Right', 'Top', 'Left']
            partner_pos = positions[(self.player_index + 2) % 4]

            # Build bid history from raw state
            bid_history = []
            raw_bids = self.raw_state.get('bidHistory', [])
            for b in raw_bids:
                bid_history.append({
                    'player': b.get('player', b.get('bidder', '')),
                    'action': b.get('action', b.get('type', 'PASS')),
                    'suit': b.get('suit'),
                })

            # Build trick history from raw state
            trick_history = []
            for trick in self.raw_state.get('currentRoundTricks', []):
                cards_list = []
                for tc in trick.get('cards', []):
                    card = tc.get('card', tc)
                    if isinstance(card, dict):
                        cards_list.append({
                            'position': tc.get('playedBy', ''),
                            'rank': card.get('rank', ''),
                            'suit': card.get('suit', ''),
                        })
                    elif hasattr(card, 'rank'):
                        cards_list.append({
                            'position': tc.get('playedBy', ''),
                            'rank': card.rank,
                            'suit': card.suit,
                        })
                if cards_list:
                    trick_history.append({
                        'leader': trick.get('leader', cards_list[0]['position'] if cards_list else ''),
                        'cards': cards_list,
                        'winner': trick.get('winner', ''),
                    })

            return read_partner(
                partner_position=partner_pos,
                bid_history=bid_history,
                trick_history=trick_history,
                mode=self.mode or 'SUN',
                trump_suit=self.trump,
            )
        except Exception:
            return None
