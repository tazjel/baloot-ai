"""
GameReconstructor — Logic to rebuild game state from captured events.
"""
from typing import List, Dict, Optional
from dataclasses import replace
from .models import GameEvent, BoardState, PlayerState

class GameReconstructor:
    """
    Maintains a rolling game state by applying sequential events.
    """
    def __init__(self):
        self.state = BoardState()
        self.reset()

    def reset(self):
        """Reset state to initial empty values."""
        self.state = BoardState(
            players=[PlayerState() for _ in range(4)],
            center_cards=[],
            scores={"US": 0, "THEM": 0}
        )

    def apply_event(self, event: GameEvent):
        """Update internal state based on event action and fields."""
        action = event.action
        f = event.fields
        
        self.state.event_index += 1
        self.state.last_action = action

        if action == "game_info":
            self._handle_game_info(f)
        elif action == "game_state":
            self._handle_game_state(f)
        elif action == "card_played":
            self._handle_card_played(f)
        elif action == "cards_eating":
            self._handle_cards_eating(f)
        elif action == "a_bid" or action == "u_bid":
            self._handle_bid(f)
        elif action == "round_over":
            self._handle_round_over(f)

    def _handle_game_info(self, f: dict):
        """Initial game setup with player names and positions."""
        players_data = f.get("players", [])
        for i, p_data in enumerate(players_data):
            if i < 4:
                self.state.players[i].id = p_data.get("id", -1)
                self.state.players[i].name = p_data.get("name", "Unknown")
                # Position mapping usually depends on local player (id 0 or 1)
                # For now, we'll use raw order or indices
                positions = ["BOTTOM", "RIGHT", "TOP", "LEFT"]
                self.state.players[i].position = positions[i]

    def _handle_game_state(self, f: dict):
        """Updates hands, current player, and dealer."""
        self.state.phase = f.get("phase", self.state.phase)
        self.state.dealer_id = f.get("dealerId", self.state.dealer_id)
        self.state.current_player_id = f.get("activePlayerId", self.state.current_player_id)
        
        # Update hands if present
        hands = f.get("hands", {})
        for p in self.state.players:
            p_id_str = str(p.id)
            if p_id_str in hands:
                p.hand = hands[p_id_str]
            
            p.is_dealer = (p.id == self.state.dealer_id)

    def _handle_card_played(self, f: dict):
        """Moves a card from hand to center."""
        player_id = f.get("playerId")
        card = f.get("card")
        if card:
            self.state.center_cards.append(card)
            # Remove from hand
            for p in self.state.players:
                if p.id == player_id:
                    if card in p.hand:
                        p.hand.remove(card)
                    break
        
        # Usually card_played triggers active player change
        # but the next game_state or event might update it more reliably

    def _handle_cards_eating(self, f: dict):
        """Clears the center cards after a trick is taken."""
        self.state.center_cards = []

    def _handle_bid(self, f: dict):
        """Updates contract and trump suit."""
        contract = f.get("bidType")
        suit = f.get("suit")
        if contract and contract != "PASS":
            self.state.contract = contract
            self.state.trump_suit = suit

    def _handle_round_over(self, f: dict):
        """Updates scores at end of round."""
        scores = f.get("scores", {})
        if scores:
            self.state.scores["US"] = scores.get("us", 0)
            self.state.scores["THEM"] = scores.get("them", 0)

    def get_snapshot(self) -> BoardState:
        """Return a deep copy of current state."""
        import copy
        return copy.deepcopy(self.state)

def reconstruct_timeline(events: List[GameEvent]) -> List[BoardState]:
    """Rebuild full timeline of states from a sequence of events."""
    reconstructor = GameReconstructor()
    timeline = []
    for event in events:
        reconstructor.apply_event(event)
        timeline.append(reconstructor.get_snapshot())
    return timeline
