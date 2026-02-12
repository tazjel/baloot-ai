"""
Game Lifecycle - Round and Game State Management
================================================

Handles the flow of the game:
- Starting the game
- Resetting round state
- Dealing cards
- Ending rounds and matches

Extracted from game.py to reduce complexity.
"""

import random
import copy
from typing import List, Dict, Any, Optional

from game_engine.models.constants import GamePhase
from game_engine.models.deck import Deck
from game_engine.models.player import Player
from game_engine.logic.utils import sort_hand
from game_engine.core.state import GameState

# We can import these lazily inside methods if circular imports are an issue, 
# but usually logic modules don't import the main Game class (except for type hints if needed).
# Here we receive `game` instance in __init__.

class GameLifecycle:
    def __init__(self, game):
        self.game = game

    def start_game(self) -> bool:
        """Initialize game state and start the first round."""
        if len(self.game.players) < 4:
            return False

        self.reset_round_state()
        self.game.dealer_index = random.randint(0, 3)
        self.deal_initial_cards()
        self.game.phase = GamePhase.BIDDING.value

        # Lazily import BiddingEngine to avoid circular dependency if any
        # (Though usually BiddingEngine is independent)
        from game_engine.logic.bidding_engine import BiddingEngine
        
        self.game.bidding_engine = BiddingEngine(
            dealer_index=self.game.dealer_index, 
            floor_card=self.game._floor_card_obj,
            players=self.game.players, 
            match_scores=self.game.match_scores,
        )
        self.game.current_turn = self.game.bidding_engine.current_turn
        self.game.reset_timer()
        return True

    def reset_round_state(self):
        """Clear all round-specific data for a fresh start."""
        self.game.deck = Deck()
        for p in self.game.players:
            p.hand = []
            p.captured_cards = []
            p.action_text = ''
        
        self.game.table_cards = []
        self.game._floor_card_obj = None
        self.game.state.reset_round()
        self.game.graveyard.reset()
        
        # Reset sub-systems
        if hasattr(self.game, 'qayd_engine'):
            self.game.qayd_engine.reset()
            self.game.qayd_state = self.game.qayd_engine.state
            
        # akka_state and sawa_state are reset by state.reset_round() automatically
        self.game.reset_timer()

    def deal_initial_cards(self):
        """Deal 5 cards to each player + 1 floor card."""
        for p in self.game.players:
            p.hand.extend(self.game.deck.deal(5))
        
        val = self.game.deck.deal(1)
        if val:
            self.game.floor_card = val[0] # Setter property on Game handles _floor_card_obj assignment

    def complete_deal(self, bidder_index: int):
        """
        Finish dealing cards after bidding is won.
        Bidder gets floor card + 2 extra cards.
        Others get 3 cards.
        """
        bidder = self.game.players[bidder_index]
        
        # Give floor card to bidder
        if self.game._floor_card_obj:
            bidder.hand.append(self.game._floor_card_obj)
            self.game.floor_card = None
            
        # Deal remaining cards
        bidder.hand.extend(self.game.deck.deal(2))
        for p in self.game.players:
            if p.index != bidder_index:
                p.hand.extend(self.game.deck.deal(3))
                
        # Sort hands and update initial snapshots
        for p in self.game.players:
            p.hand = sort_hand(p.hand, self.game.game_mode, self.game.trump_suit)
            p.action_text = ""
            self.game.initial_hands[p.position] = [c.to_dict() for c in p.hand]
            
        self.game.phase = GamePhase.PLAYING.value
        self.game.current_turn = (self.game.dealer_index + 1) % 4
        self.game.reset_timer()

        # Auto-declare projects for all bots at start of play
        if hasattr(self.game, 'project_manager'):
            self.game.project_manager.auto_declare_bot_projects()

    def end_round(self, skip_scoring: bool = False):
        """
        Finalize the round, calculate scores, and prepare for next round or game over.
        """
        self.game._record("ROUND_END")
        
        if not skip_scoring:
            rr, su, st = self.game.scoring_engine.calculate_final_scores()
            self.game.past_round_results.append(rr)
            self.game.match_scores['us'] += su
            self.game.match_scores['them'] += st
            
            snap = self.game._build_round_snapshot(rr)
            self.game.full_match_history.append(snap)
            
            # Notify AI agent
            try:
                from ai_worker.agent import bot_agent
                bot_agent.capture_round_data(snap)
            except Exception: 
                pass

        # Advance dealer
        self.game.dealer_index = (self.game.dealer_index + 1) % 4
        
        # Check game over condition
        if self.game.match_scores['us'] >= 152 or self.game.match_scores['them'] >= 152:
            self.game.phase = GamePhase.GAMEOVER.value
            try:
                from server.services.archiver import archive_match
                archive_match(self.game)
            except Exception: 
                pass
        else:
            self.game.phase = GamePhase.FINISHED.value
            
        self.game.sawa_failed_khasara = False
        self.game.reset_timer()
