
import logging
from typing import List
from ai_worker.bot_context import BotContext
from game_engine.models.card import Card
from game_engine.models.constants import SUITS, RANKS, ORDER_SUN, ORDER_HOKUM

logger = logging.getLogger(__name__)

class FeatureExtractor:
    """
    Converts BotContext into a fixed-size numerical vector.
    Vector Size: 32 (Hand) + 32 (Table) + 32 (Played) + 32 (Legal) + 10 (Context) = 138 Features.
    """
    
    def __init__(self):
        # Card Map: (Suit, Rank) -> Index 0-31
        self.card_to_idx = {}
        
        # Mapping S/H/D/C to standard SUITS indices 
        # Standard constants.SUITS = ['♠', '♥', '♦', '♣'] (0, 1, 2, 3)
        # We want S->0, H->1, D->2, C->3 as well.
        
        self.suit_map = {
            'S': '♠', 's': '♠', '♠': '♠',
            'H': '♥', 'h': '♥', '♥': '♥',
            'D': '♦', 'd': '♦', '♦': '♦',
            'C': '♣', 'c': '♣', '♣': '♣'
        }
        
        raw_suits_order = ['♠', '♥', '♦', '♣']
        
        idx = 0
        for s in raw_suits_order:
            for r in RANKS:
                # Key using standardized suit
                key = f"{s}{r}"
                self.card_to_idx[key] = idx
                idx += 1

    def encode(self, ctx: BotContext, legal_moves_indices: List[int] = None) -> List[float]:
        # Initialize zero vector
        # Size = 32*4 + 10 = 138
        vec = [0.0] * 138
        
        # 1. Hand (0-31)
        # Note: ctx.hand is a list of Card objects
        for i, card in enumerate(ctx.hand):
            c_idx = self._get_card_index(card)
            if c_idx >= 0:
                vec[0 + c_idx] = 1.0
                
        # 2. Table (32-63)
        # ctx.raw_state['tableCards'] = [{'card': {suit, rank}, playedBy: ...}]
        table_cards = ctx.raw_state.get('tableCards', [])
        for item in table_cards:
            c_data = item.get('card')
            if c_data:
                # Handle dict or obj
                if isinstance(c_data, dict):
                    c_obj = Card(c_data['suit'], c_data['rank'])
                else:
                    c_obj = c_data
                c_idx = self._get_card_index(c_obj)
                if c_idx >= 0:
                    vec[32 + c_idx] = 1.0
                    
        # 3. Played History (64-95)
        # Assuming ctx.memory.played_cards contains string representations from __str__ or similar
        # Ideally we iterate over all possible cards and check if they are in memory.
        # But for MVP we can skip expensive loop if needed. 
        # Let's keep it simple for now and leave it as zeros unless we want to iterate.
        pass 
            
        # 4. Legal Moves Mask (96-127)
        if legal_moves_indices and ctx.hand:
            for idx in legal_moves_indices:
                if idx < len(ctx.hand):
                    card = ctx.hand[idx]
                    c_idx = self._get_card_index(card)
                    if c_idx >= 0:
                        vec[96 + c_idx] = 1.0
        
        # 5. Context (128-137)
        base = 128
        
        trump = ctx.trump
        mode = ctx.mode 
        
        # Normalize Trump String
        norm_trump = self.suit_map.get(trump, None)
        if norm_trump and norm_trump in SUITS:
            t_idx = SUITS.index(norm_trump)
            vec[base + t_idx] = 1.0
            
        if mode == 'SUN':
            vec[base + 4] = 1.0
        else:
            vec[base + 5] = 1.0
            
        # Scores (Normalized / 152)
        scores = ctx.raw_state.get('matchScores', {})
        us = scores.get('us', 0) / 152.0
        them = scores.get('them', 0) / 152.0
        vec[base + 6] = us
        vec[base + 7] = them
        
        # Is Leading? (Table empty)
        if not table_cards:
            vec[base + 8] = 1.0
            
        return vec

    def _get_card_index(self, card: Card) -> int:
        normalized_suit = self.suit_map.get(card.suit, card.suit)
        key = f"{normalized_suit}{card.rank}"
        return self.card_to_idx.get(key, -1)

    def encode_fast(self, game, legal_moves_indices: List[int] = None) -> List[float]:
        """
        Optimized encoder for FastGame state (MCTS).
        'game' is typed as 'FastGame' but dynamic here to avoid circular imports.
        """
        # Initialize zero vector
        vec = [0.0] * 138
        
        # 1. Hand (0-31)
        # FastGame Hands are List[Card]
        # Current Turn Player's Hand
        hand = game.hands[game.current_turn]
        for i, card in enumerate(hand):
            c_idx = self._get_card_index(card)
            if c_idx >= 0:
                vec[0 + c_idx] = 1.0
                
        # 2. Table (32-63)
        # FastGame table is List[Tuple[player_idx, Card]]
        for p_idx, card in game.played_cards_in_trick:
            c_idx = self._get_card_index(card)
            if c_idx >= 0:
                vec[32 + c_idx] = 1.0
                    
        # 3. Played History (64-95)
        # FastGame doesn't track full history strictly in a hashset for lookup?
        # It has tricks_history.
        # Check game.tricks_history: List of previous ticks?
        # FastGame definition: self.tricks_history = tricks_history if tricks_history else []
        # Usually empty in lightweight clones unless we copy it.
        # Skip for speed in MCTS.
        pass
            
        # 4. Legal Moves Mask (96-127)
        if legal_moves_indices:
            for idx in legal_moves_indices:
                if idx < len(hand):
                    card = hand[idx]
                    c_idx = self._get_card_index(card)
                    if c_idx >= 0:
                        vec[96 + c_idx] = 1.0
        
        # 5. Context (128-137)
        base = 128
        
        trump = game.trump
        mode = game.mode 
        
        # Normalize Trump String
        norm_trump = self.suit_map.get(trump, None)
        if norm_trump and norm_trump in SUITS:
            t_idx = SUITS.index(norm_trump)
            vec[base + t_idx] = 1.0
            
        if mode == 'SUN':
            vec[base + 4] = 1.0
        else:
            vec[base + 5] = 1.0
            
        # Scores (Normalized / 152)
        # FastGame uses 'us'/'them'
        us = game.scores.get('us', 0) / 152.0
        them = game.scores.get('them', 0) / 152.0
        vec[base + 6] = us
        vec[base + 7] = them
        
        # Is Leading? (Table empty)
        if not game.played_cards_in_trick:
            vec[base + 8] = 1.0
            
        return vec

