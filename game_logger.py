"""
Game Logger - Centralized logging utility for Baloot game testing

Provides configurable logging levels, formatted output, and game state inspection
for CLI testing and debugging.
"""

import logging
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import sys


class LogLevel(Enum):
    """Log verbosity levels"""
    QUIET = 0      # Only errors and final results
    NORMAL = 1     # Key events (bids, trick winners, scores)
    VERBOSE = 2    # Detailed events (all plays, validations)
    DEBUG = 3      # Full game state dumps


class Colors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'


class GameLogger:
    """Centralized logger for game events and state"""
    
    def __init__(self, level: LogLevel = LogLevel.NORMAL, log_file: Optional[str] = None, use_colors: bool = True):
        """
        Initialize game logger
        
        Args:
            level: Logging verbosity level
            log_file: Optional file path for log output
            use_colors: Whether to use colored output in console
        """
        self.level = level
        self.log_file = log_file
        self.use_colors = use_colors and sys.stdout.isatty()
        self.file_handle = None
        
        if self.log_file:
            try:
                self.file_handle = open(self.log_file, 'w', encoding='utf-8')
                self._write_to_file(f"=== Game Log Started at {datetime.now().isoformat()} ===\n")
            except Exception as e:
                print(f"Warning: Could not open log file {log_file}: {e}")
    
    def __del__(self):
        """Close log file on cleanup"""
        if self.file_handle:
            self.file_handle.close()
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled"""
        if self.use_colors:
            return f"{color}{text}{Colors.RESET}"
        return text
    
    def _write_to_file(self, message: str):
        """Write message to log file"""
        if self.file_handle:
            # Strip ANSI codes for file output
            import re
            clean_message = re.sub(r'\033\[[0-9;]+m', '', message)
            self.file_handle.write(clean_message + '\n')
            self.file_handle.flush()
    
    def _log(self, message: str, min_level: LogLevel = LogLevel.NORMAL, color: str = Colors.RESET):
        """Internal logging method"""
        if self.level.value >= min_level.value:
            colored_msg = self._colorize(message, color)
            print(colored_msg)
            self._write_to_file(message)
    
    # === Event Logging Methods ===
    
    def header(self, text: str):
        """Log a section header"""
        separator = "=" * 60
        self._log(f"\n{separator}", LogLevel.QUIET, Colors.BOLD + Colors.CYAN)
        self._log(f"{text}", LogLevel.QUIET, Colors.BOLD + Colors.CYAN)
        self._log(f"{separator}", LogLevel.QUIET, Colors.BOLD + Colors.CYAN)
    
    def subheader(self, text: str):
        """Log a subsection header"""
        self._log(f"\n--- {text} ---", LogLevel.NORMAL, Colors.BOLD + Colors.BLUE)
    
    def info(self, message: str, min_level: LogLevel = LogLevel.NORMAL):
        """Log informational message"""
        self._log(f"ℹ {message}", min_level, Colors.CYAN)
    
    def success(self, message: str, min_level: LogLevel = LogLevel.NORMAL):
        """Log success message"""
        self._log(f"✓ {message}", min_level, Colors.BRIGHT_GREEN)
    
    def warning(self, message: str, min_level: LogLevel = LogLevel.NORMAL):
        """Log warning message"""
        self._log(f"⚠ {message}", min_level, Colors.BRIGHT_YELLOW)
    
    def error(self, message: str):
        """Log error message (always shown)"""
        self._log(f"✗ {message}", LogLevel.QUIET, Colors.BRIGHT_RED)
    
    def debug(self, message: str):
        """Log debug message"""
        self._log(f"[DEBUG] {message}", LogLevel.DEBUG, Colors.MAGENTA)
    
    # === Game Event Logging ===
    
    def game_start(self, room_id: str, dealer_index: int):
        """Log game start"""
        self.header(f"GAME START - Room: {room_id}")
        self.info(f"Dealer: Player {dealer_index}", LogLevel.NORMAL)
    
    def round_start(self, round_num: int):
        """Log round start"""
        self.subheader(f"Round {round_num}")
    
    def deal_cards(self, player_index: int, hand: List[Dict]):
        """Log card dealing"""
        hand_str = self._format_hand(hand)
        self.debug(f"Player {player_index} dealt: {hand_str}")
    
    def bid_action(self, player_index: int, player_name: str, action: str, suit: Optional[str] = None):
        """Log bidding action"""
        bid_str = f"{action}"
        if suit:
            bid_str += f" ({suit})"
        
        color = Colors.BRIGHT_YELLOW if action in ['SUN', 'HOKUM', 'ASHKAL'] else Colors.WHITE
        self._log(f"  Player {player_index} ({player_name}): {bid_str}", LogLevel.NORMAL, color)
    
    def bid_winner(self, player_index: int, bid_type: str, trump_suit: Optional[str] = None):
        """Log bid winner"""
        bid_str = f"{bid_type}"
        if trump_suit:
            bid_str += f" - Trump: {trump_suit}"
        self.success(f"Bid won by Player {player_index}: {bid_str}", LogLevel.NORMAL)
    
    def play_card(self, player_index: int, player_name: str, card: Dict, card_index: int):
        """Log card play"""
        card_str = self._format_card(card)
        self._log(f"  Player {player_index} ({player_name}) plays: {card_str} (index {card_index})", 
                  LogLevel.NORMAL, Colors.BRIGHT_CYAN)
    
    def trick_winner(self, player_index: int, player_name: str, team: str, points: int):
        """Log trick winner"""
        color = Colors.BRIGHT_GREEN if team == 'us' else Colors.BRIGHT_MAGENTA
        self.success(f"Trick won by Player {player_index} ({player_name}) - Team: {team} - Points: {points}", 
                    LogLevel.NORMAL)
    
    def project_declared(self, player_index: int, project_type: str, cards: List[Dict]):
        """Log project declaration"""
        cards_str = self._format_hand(cards)
        self._log(f"  Player {player_index} declares {project_type}: {cards_str}", 
                  LogLevel.NORMAL, Colors.BRIGHT_YELLOW)
    
    def round_end(self, us_score: int, them_score: int, winner: str):
        """Log round end"""
        self.subheader("ROUND END")
        self.info(f"Us: {us_score} points", LogLevel.NORMAL)
        self.info(f"Them: {them_score} points", LogLevel.NORMAL)
        
        color = Colors.BRIGHT_GREEN if winner == 'us' else Colors.BRIGHT_MAGENTA
        self._log(f"Winner: {winner.upper()}", LogLevel.NORMAL, color)
    
    def match_scores(self, us_total: int, them_total: int):
        """Log match scores"""
        self.info(f"Match Score - Us: {us_total} | Them: {them_total}", LogLevel.QUIET)
    
    def game_over(self, winner: str, us_total: int, them_total: int):
        """Log game over"""
        self.header(f"GAME OVER - Winner: {winner.upper()}")
        self.match_scores(us_total, them_total)
    
    # === Game State Display ===
    
    def display_game_state(self, game_state: Dict):
        """Display formatted game state"""
        if self.level.value < LogLevel.VERBOSE.value:
            return
        
        self.subheader("GAME STATE")
        
        # Phase
        phase = game_state.get('phase', 'UNKNOWN')
        self.info(f"Phase: {phase}", LogLevel.VERBOSE)
        
        # Current turn
        current_turn = game_state.get('currentTurn', -1)
        if current_turn >= 0:
            self.info(f"Current Turn: Player {current_turn}", LogLevel.VERBOSE)
        
        # Bid info
        bid = game_state.get('bid', {})
        if bid.get('type'):
            bid_str = f"{bid['type']}"
            if bid.get('suit'):
                bid_str += f" ({bid['suit']})"
            self.info(f"Bid: {bid_str} by Player {bid.get('playerIndex', '?')}", LogLevel.VERBOSE)
        
        # Table cards
        table_cards = game_state.get('tableCards', [])
        if table_cards:
            self.info(f"Table Cards: {len(table_cards)}", LogLevel.VERBOSE)
            for tc in table_cards:
                card_str = self._format_card(tc['card'])
                self._log(f"    {tc['playedBy']}: {card_str}", LogLevel.VERBOSE, Colors.CYAN)
        
        # Scores
        team_scores = game_state.get('teamScores', {})
        if team_scores:
            self.info(f"Round Scores - Us: {team_scores.get('us', 0)} | Them: {team_scores.get('them', 0)}", 
                     LogLevel.VERBOSE)
        
        match_scores = game_state.get('matchScores', {})
        if match_scores:
            self.info(f"Match Scores - Us: {match_scores.get('us', 0)} | Them: {match_scores.get('them', 0)}", 
                     LogLevel.VERBOSE)
    
    def display_player_hand(self, player_index: int, hand: List[Dict]):
        """Display player's hand"""
        hand_str = self._format_hand(hand)
        self.info(f"Player {player_index} Hand: {hand_str}", LogLevel.VERBOSE)
    
    def display_all_hands(self, players: List[Dict]):
        """Display all players' hands (for debugging)"""
        if self.level.value < LogLevel.DEBUG.value:
            return
        
        self.subheader("ALL HANDS (DEBUG)")
        for player in players:
            hand_str = self._format_hand(player.get('hand', []))
            self.debug(f"Player {player['index']} ({player['name']}): {hand_str}")
    
    def dump_game_state(self, game_state: Dict):
        """Dump full game state as JSON (debug only)"""
        if self.level.value >= LogLevel.DEBUG.value:
            self.debug("Full Game State:")
            self.debug(json.dumps(game_state, indent=2))
    
    # === Formatting Helpers ===
    
    def _format_card(self, card) -> str:
        """Format a card for display"""
        if not card:
            return "None"
        
        # Handle both Card objects and dictionaries
        if hasattr(card, 'rank') and hasattr(card, 'suit'):
            # Card object
            return f"{card.rank}{card.suit}"
        elif isinstance(card, dict):
            # Dictionary
            rank = card.get('rank', '?')
            suit = card.get('suit', '?')
            return f"{rank}{suit}"
        else:
            return str(card)
    
    def _format_hand(self, hand: List[Dict]) -> str:
        """Format a hand of cards for display"""
        if not hand:
            return "[]"
        return "[" + ", ".join(self._format_card(c) for c in hand) + "]"
    
    # === Assertion Helpers ===
    
    def assert_equal(self, actual: Any, expected: Any, message: str = ""):
        """Assert equality and log result"""
        if actual == expected:
            self.success(f"Assertion passed: {message}", LogLevel.VERBOSE)
            return True
        else:
            self.error(f"Assertion failed: {message}")
            self.error(f"  Expected: {expected}")
            self.error(f"  Actual: {actual}")
            return False
    
    def assert_phase(self, game_state: Dict, expected_phase: str):
        """Assert game is in expected phase"""
        actual_phase = game_state.get('phase', 'UNKNOWN')
        return self.assert_equal(actual_phase, expected_phase, f"Game phase should be {expected_phase}")
    
    def assert_winner(self, game_state: Dict, expected_winner: str):
        """Assert expected winner"""
        # This would need to be called after game ends
        return self.assert_equal(game_state.get('winner'), expected_winner, f"Winner should be {expected_winner}")


# Singleton instance for easy access
_default_logger: Optional[GameLogger] = None


def get_logger() -> GameLogger:
    """Get the default logger instance"""
    global _default_logger
    if _default_logger is None:
        _default_logger = GameLogger()
    return _default_logger


def set_logger(logger: GameLogger):
    """Set the default logger instance"""
    global _default_logger
    _default_logger = logger
