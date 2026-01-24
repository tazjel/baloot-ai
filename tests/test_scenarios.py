"""
Test Scenarios - Predefined test scenarios for Baloot game testing

Provides various test scenarios including full games, bidding tests, project tests,
edge cases, and stress testing.
"""

from typing import Dict, List, Optional, Callable
from server.game_logic import Game, SUITS, RANKS
import random


class ScenarioBase:
    """Base class for test scenarios"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def setup(self, game: Game) -> bool:
        """
        Setup the scenario (e.g., deal specific hands)
        Returns True if setup successful
        """
        return True
    
    def validate(self, game: Game) -> Dict:
        """
        Validate the scenario outcome
        Returns dict with 'success' and 'message'
        """
        return {'success': True, 'message': 'No validation defined'}


class FullGameScenario(ScenarioBase):
    """Complete game from start to finish"""
    
    def __init__(self):
        super().__init__(
            name="Full Game",
            description="Complete game with random hands, plays until FINISHED or GAMEOVER"
        )
    
    def validate(self, game: Game) -> Dict:
        """Validate game completed"""
        if game.phase in ['FINISHED', 'GAMEOVER']:
            return {
                'success': True,
                'message': f"Game completed in phase {game.phase}"
            }
        else:
            return {
                'success': False,
                'message': f"Game did not complete, stuck in phase {game.phase}"
            }


class BiddingTestScenario(ScenarioBase):
    """Test various bidding strategies"""
    
    def __init__(self, bid_type: str = 'SUN'):
        super().__init__(
            name=f"Bidding Test - {bid_type}",
            description=f"Test {bid_type} bidding with strong hands"
        )
        self.bid_type = bid_type
    
    def setup(self, game: Game) -> bool:
        """Give first player a strong hand for the bid type"""
        if self.bid_type == 'SUN':
            # Strong SUN hand: Multiple Aces and Tens
            strong_hand = [
                {'rank': 'A', 'suit': 'S', 'id': 'AS'},
                {'rank': 'A', 'suit': 'H', 'id': 'AH'},
                {'rank': '10', 'suit': 'S', 'id': '10S'},
                {'rank': '10', 'suit': 'H', 'id': '10H'},
                {'rank': 'K', 'suit': 'D', 'id': 'KD'},
            ]
            game.players[0].hand = strong_hand
        
        elif self.bid_type == 'HOKUM':
            # Strong HOKUM hand: Jack, 9, Ace in one suit
            strong_hand = [
                {'rank': 'J', 'suit': 'S', 'id': 'JS'},
                {'rank': '9', 'suit': 'S', 'id': '9S'},
                {'rank': 'A', 'suit': 'S', 'id': 'AS'},
                {'rank': '10', 'suit': 'S', 'id': '10S'},
                {'rank': 'A', 'suit': 'H', 'id': 'AH'},
            ]
            game.players[0].hand = strong_hand
        
        elif self.bid_type == 'ASHKAL':
            # Very strong SUN hand for ASHKAL
            strong_hand = [
                {'rank': 'A', 'suit': 'S', 'id': 'AS'},
                {'rank': 'A', 'suit': 'H', 'id': 'AH'},
                {'rank': 'A', 'suit': 'D', 'id': 'AD'},
                {'rank': '10', 'suit': 'S', 'id': '10S'},
                {'rank': '10', 'suit': 'H', 'id': '10H'},
            ]
            game.players[0].hand = strong_hand
        
        return True
    
    def validate(self, game: Game) -> Dict:
        """Validate bid was made"""
        if game.bid.get('type'):
            return {
                'success': True,
                'message': f"Bid made: {game.bid['type']}"
            }
        else:
            return {
                'success': False,
                'message': "No bid was made"
            }


class ProjectTestScenario(ScenarioBase):
    """Test project declarations"""
    
    def __init__(self, project_type: str = 'FOUR'):
        super().__init__(
            name=f"Project Test - {project_type}",
            description=f"Test {project_type} project declaration"
        )
        self.project_type = project_type
    
    def setup(self, game: Game) -> bool:
        """Give players hands with projects"""
        if self.project_type == 'FOUR':
            # Four of a kind
            project_hand = [
                {'rank': 'K', 'suit': 'S', 'id': 'KS'},
                {'rank': 'K', 'suit': 'H', 'id': 'KH'},
                {'rank': 'K', 'suit': 'D', 'id': 'KD'},
                {'rank': 'K', 'suit': 'C', 'id': 'KC'},
                {'rank': '7', 'suit': 'S', 'id': '7S'},
            ]
            game.players[0].hand = project_hand
        
        elif self.project_type == 'SEQUENCE':
            # Sequence of 3+ cards
            project_hand = [
                {'rank': 'A', 'suit': 'S', 'id': 'AS'},
                {'rank': 'K', 'suit': 'S', 'id': 'KS'},
                {'rank': 'Q', 'suit': 'S', 'id': 'QS'},
                {'rank': 'J', 'suit': 'S', 'id': 'JS'},
                {'rank': '7', 'suit': 'H', 'id': '7H'},
            ]
            game.players[0].hand = project_hand
        
        elif self.project_type == 'BALOOT':
            # K and Q of trump (only valid in HOKUM)
            project_hand = [
                {'rank': 'K', 'suit': 'S', 'id': 'KS'},
                {'rank': 'Q', 'suit': 'S', 'id': 'QS'},
                {'rank': 'J', 'suit': 'S', 'id': 'JS'},
                {'rank': '9', 'suit': 'S', 'id': '9S'},
                {'rank': 'A', 'suit': 'H', 'id': 'AH'},
            ]
            game.players[0].hand = project_hand
            # Force HOKUM bid with Spades as trump
            game.bid = {'type': 'HOKUM', 'suit': 'S', 'playerIndex': 0}
            game.phase = 'PLAYING'
        
        return True
    
    def validate(self, game: Game) -> Dict:
        """Validate project was declared"""
        # Check if any player has declared projects
        for player in game.players:
            if hasattr(player, 'declared_projects') and player.declared_projects:
                return {
                    'success': True,
                    'message': f"Project declared: {player.declared_projects}"
                }
        
        return {
            'success': False,
            'message': "No projects were declared"
        }


class SawaTestScenario(ScenarioBase):
    """Test Sawa (Sawa) - claiming all remaining tricks"""
    
    def __init__(self):
        super().__init__(
            name="Sawa Test",
            description="Test Sawa (Sawa) claim functionality"
        )
    
    def setup(self, game: Game) -> bool:
        """Setup a scenario where Sawa is likely"""
        # Give player very strong hand
        strong_hand = [
            {'rank': 'A', 'suit': 'S', 'id': 'AS'},
            {'rank': 'A', 'suit': 'H', 'id': 'AH'},
            {'rank': 'A', 'suit': 'D', 'id': 'AD'},
            {'rank': 'A', 'suit': 'C', 'id': 'AC'},
            {'rank': '10', 'suit': 'S', 'id': '10S'},
        ]
        game.players[0].hand = strong_hand
        return True


class DoubleTestScenario(ScenarioBase):
    """Test doubling functionality"""
    
    def __init__(self):
        super().__init__(
            name="Double Test",
            description="Test game doubling by opponents"
        )
    
    def setup(self, game: Game) -> bool:
        """Setup scenario for doubling"""
        # Give bidder a moderate hand, opponents strong hands
        return True


class StressTestScenario(ScenarioBase):
    """Stress test - multiple consecutive games"""
    
    def __init__(self, num_games: int = 10):
        super().__init__(
            name=f"Stress Test ({num_games} games)",
            description=f"Run {num_games} consecutive games to test stability"
        )
        self.num_games = num_games
        self.completed_games = 0
    
    def validate(self, game: Game) -> Dict:
        """Validate all games completed"""
        self.completed_games += 1
        
        if self.completed_games >= self.num_games:
            return {
                'success': True,
                'message': f"All {self.num_games} games completed successfully"
            }
        else:
            return {
                'success': True,
                'message': f"Game {self.completed_games}/{self.num_games} completed"
            }


class EdgeCaseScenario(ScenarioBase):
    """Test edge cases and unusual situations"""
    
    def __init__(self, case_type: str = 'all_pass'):
        super().__init__(
            name=f"Edge Case - {case_type}",
            description=f"Test edge case: {case_type}"
        )
        self.case_type = case_type
    
    def setup(self, game: Game) -> bool:
        """Setup edge case scenario"""
        if self.case_type == 'all_pass':
            # Give all players weak hands to encourage passing
            weak_hand = [
                {'rank': '7', 'suit': 'S', 'id': '7S'},
                {'rank': '8', 'suit': 'H', 'id': '8H'},
                {'rank': '7', 'suit': 'D', 'id': '7D'},
                {'rank': '8', 'suit': 'C', 'id': '8C'},
                {'rank': '7', 'suit': 'H', 'id': '7H'},
            ]
            for player in game.players:
                player.hand = weak_hand.copy()
        
        return True


# === Scenario Registry ===

SCENARIOS = {
    'full_game': FullGameScenario(),
    'bidding_sun': BiddingTestScenario('SUN'),
    'bidding_hokum': BiddingTestScenario('HOKUM'),
    'bidding_ashkal': BiddingTestScenario('ASHKAL'),
    'project_four': ProjectTestScenario('FOUR'),
    'project_sequence': ProjectTestScenario('SEQUENCE'),
    'project_baloot': ProjectTestScenario('BALOOT'),
    'sawa_test': SawaTestScenario(),
    'double_test': DoubleTestScenario(),
    'stress_test': StressTestScenario(10),
    'edge_all_pass': EdgeCaseScenario('all_pass'),
}


def get_scenario(name: str) -> Optional[ScenarioBase]:
    """Get a scenario by name"""
    return SCENARIOS.get(name)


def list_scenarios() -> List[str]:
    """List all available scenario names"""
    return list(SCENARIOS.keys())


def get_scenario_info(name: str) -> Optional[Dict]:
    """Get scenario information"""
    scenario = get_scenario(name)
    if scenario:
        return {
            'name': scenario.name,
            'description': scenario.description
        }
    return None
