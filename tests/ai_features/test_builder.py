from typing import List, Dict, Optional, Any
from game_engine.logic.game import Game
from game_engine.models.player import Player
from game_engine.models.card import Card
from game_engine.models.constants import GamePhase, BiddingPhase, BidType

class TestBuilder:
    def __init__(self):
        self.game = Game("test_room")
        # Default initialization with 4 players
        self.game.players = [
            Player("p1", "Player 1", 0, self.game),
            Player("p2", "Player 2", 1, self.game),
            Player("p3", "Player 3", 2, self.game),
            Player("p4", "Player 4", 3, self.game)
        ]
        self.game.dealer_index = 0
        self.game.current_turn = 1
        
    def with_mode(self, mode: str):
        self.game.game_mode = mode
        return self

    def with_trump(self, suit: str):
        self.game.trump_suit = suit
        return self
        
    def with_phase(self, phase: str):
        # Map string to Enum value if needed, strict for now
        self.game.phase = phase
        return self

    def with_bid(self, type: str, suit: str = None, bidder_idx: int = 0):
        self.game.bid = {
            "type": type,
            "suit": suit,
            "bidder": self.game.players[bidder_idx].position,
            "doubled": False,
            "level": 1
        }
        return self

    def with_hand(self, player_idx: int, card_strs: List[str]):
        """
        Populate a player's hand using short codes.
        e.g. ["AS", "10H", "KD"] -> [Card('S', 'A'), Card('H', '10'), Card('D', 'K')]
        """
        cards = []
        for s in card_strs:
            cards.append(self._parse_card(s))
        self.game.players[player_idx].hand = cards
        return self

    def with_table(self, plays: List[Dict[str, Any]]):
        """
        Setup table cards.
        plays: List of {'p_idx': 0, 'card': 'AS', 'illegal': False}
        """
        self.game.table_cards = []
        for p in plays:
            player = self.game.players[p['p_idx']]
            c_obj = self._parse_card(p['card'])
            entry = {
                "playerId": player.id,
                "card": c_obj,
                "playedBy": player.position,
                "metadata": {"is_illegal": True} if p.get('illegal') else {}
            }
            self.game.table_cards.append(entry)
        return self

    def _parse_card(self, s: str) -> Card:
        # Expected format: "RankSuit" or "10Suit" -> "AS", "10H", "7D"
        # Since 10 is the only 2-char rank, handle it specifically or regex
        # Simple parsing logic from utils/scenarios
        if s.startswith("10"):
            rank = "10"
            suit = s[2]
        else:
            rank = s[0]
            suit = s[1]
        
        # Validate Suit/Rank?
        return Card(suit, rank)

    def build(self) -> Game:
        # Ensure managers are initialized properly if needed
        # (Game.__init__ already handles this)
        return self.game
