#!/usr/bin/env python3
"""
CLI Test Runner - Command-line interface for testing Baloot game

Provides interactive and automated testing modes with detailed logging
and game state inspection. No browser required!

Usage:
    # Interactive mode
    python cli_test_runner.py --interactive

    # Run a specific scenario
    python cli_test_runner.py --scenario full_game --verbose

    # Run multiple games
    python cli_test_runner.py --scenario stress_test --games 10

    # Save logs to file
    python cli_test_runner.py --scenario full_game --log-file test.log

    # List available scenarios
    python cli_test_runner.py --list-scenarios
"""

import argparse
import sys
import time
import random
from typing import Dict, List, Optional

from game_logic import Game, GamePhase
from bot_agent import bot_agent
from game_logger import GameLogger, LogLevel
from test_scenarios import get_scenario, list_scenarios, get_scenario_info


class CLITestRunner:
    """CLI Test Runner for Baloot game"""
    
    def __init__(self, logger: GameLogger):
        self.logger = logger
        self.game: Optional[Game] = None
        self.stats = {
            'games_played': 0,
            'games_completed': 0,
            'games_failed': 0,
            'us_wins': 0,
            'them_wins': 0,
            'total_rounds': 0,
        }
    
    def create_game(self, room_id: str = "test_room") -> Game:
        """Create a new game instance"""
        self.game = Game(room_id)
        
        # Add 4 players (all bots by default)
        player_names = ["Player 0", "Player 1", "Player 2", "Player 3"]
        for i, name in enumerate(player_names):
            player = self.game.add_player(f"p{i}", name)
            player.is_bot = True
        
        self.logger.info(f"Created game with 4 players", LogLevel.VERBOSE)
        return self.game
    
    def run_automated_game(self, scenario_name: Optional[str] = None, max_rounds: int = 100) -> bool:
        """
        Run an automated game with bots
        
        Args:
            scenario_name: Optional scenario to run
            max_rounds: Maximum number of action rounds before timeout
        
        Returns:
            True if game completed successfully
        """
        # Create game
        game = self.create_game()
        
        # Apply scenario if specified
        scenario = None
        if scenario_name:
            scenario = get_scenario(scenario_name)
            if scenario:
                self.logger.info(f"Running scenario: {scenario.name}", LogLevel.NORMAL)
                self.logger.info(f"Description: {scenario.description}", LogLevel.NORMAL)
                scenario.setup(game)
            else:
                self.logger.error(f"Scenario '{scenario_name}' not found")
                return False
        
        # Start game
        if not game.start_game():
            self.logger.error("Failed to start game")
            return False
        
        self.logger.game_start(game.room_id, game.dealer_index)
        
        # Display initial hands (debug only)
        self.logger.display_all_hands([p.to_dict() for p in game.players])
        
        # Game loop
        round_count = 0
        last_phase = None
        
        while game.phase not in [GamePhase.FINISHED.value, GamePhase.GAMEOVER.value]:
            # Safety check
            if round_count >= max_rounds:
                self.logger.error(f"Game timeout after {max_rounds} rounds")
                self.stats['games_failed'] += 1
                return False
            
            # Track phase changes
            if game.phase != last_phase:
                self.logger.info(f"Phase changed to: {game.phase}", LogLevel.VERBOSE)
                last_phase = game.phase
            
            # Get current player
            current_player = game.players[game.current_turn]
            
            # Display game state
            self.logger.display_game_state(game.get_game_state())
            
            # Handle different phases
            if game.phase in [GamePhase.BIDDING.value, GamePhase.DOUBLING.value, GamePhase.VARIANT_SELECTION.value]:
                self._handle_bidding_turn(game, current_player)
            
            elif game.phase == GamePhase.PLAYING.value:
                self._handle_playing_turn(game, current_player)
            
            elif game.phase == GamePhase.WAITING.value:
                self.logger.error("Game stuck in WAITING phase")
                self.stats['games_failed'] += 1
                return False
            
            # Handle GABLAK_WINDOW - Wait for timeout
            game_state = game.get_game_state()
            if game_state.get('biddingPhase') == 'GABLAK_WINDOW':
                self.logger.info("Gablak Window Active - Waiting for timeout...", LogLevel.VERBOSE)
                time.sleep(5.5) # Wait for > 5s duration
                
                # Trigger an update (any call to handle_bid will trigger timeout check)
                # Call handle_bid with trivial data to force engine update
                # Or just let the loop continue, next handle_bid call will trigger timeout.
                # But we shouldn't increment round_count for this wait?
                # Actually, simply waiting is enough, next loop iteration will call handle_bid and Engine will process timeout.
                
            round_count += 1
        
        # Game ended
        self.logger.match_scores(game.match_scores['us'], game.match_scores['them'])
        
        if game.phase == GamePhase.GAMEOVER.value:
            winner = 'us' if game.match_scores['us'] >= 152 else 'them'
            self.logger.game_over(winner, game.match_scores['us'], game.match_scores['them'])
            
            if winner == 'us':
                self.stats['us_wins'] += 1
            else:
                self.stats['them_wins'] += 1
        
        # Validate scenario if provided
        if scenario:
            result = scenario.validate(game)
            if result['success']:
                self.logger.success(f"Scenario validation: {result['message']}", LogLevel.NORMAL)
            else:
                self.logger.error(f"Scenario validation failed: {result['message']}")
                self.stats['games_failed'] += 1
                return False
        
        self.stats['games_completed'] += 1
        self.stats['games_played'] += 1
        return True
    
    def _handle_bidding_turn(self, game: Game, player):
        """Handle a bidding turn"""
        # Get bot decision
        game_state = game.get_game_state()
        decision = bot_agent.get_decision(game_state, player.index)
        
        action = decision.get('action', 'PASS').upper()
        suit = decision.get('suit')
        
        # Log bid
        self.logger.bid_action(player.index, player.name, action, suit)
        
        # Execute bid
        result = game.handle_bid(player.index, action, suit)
        
        if not result.get('success'):
            self.logger.error(f"Bid failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Check if bid was won (phase changed to PLAYING)
        if game.bid.get('type') and game.phase == GamePhase.PLAYING.value:
            # Find bidder index from position
            bidder_position = game.bid.get('bidder')
            bidder_idx = next((p.index for p in game.players if p.position == bidder_position), 0)
            self.logger.bid_winner(bidder_idx, game.bid['type'], game.bid.get('suit'))
        
        return True
    
    def _handle_playing_turn(self, game: Game, player):
        """Handle a playing turn"""
        # Get bot decision
        game_state = game.get_game_state()
        decision = bot_agent.get_decision(game_state, player.index)
        
        card_index = decision.get('cardIndex', 0)
        
        # Validate card index
        if card_index < 0 or card_index >= len(player.hand):
            self.logger.error(f"Invalid card index: {card_index}")
            return False
        
        card = player.hand[card_index]
        
        # Log play
        self.logger.play_card(player.index, player.name, card, card_index)
        
        # Execute play
        result = game.play_card(player.index, card_index)
        
        if not result.get('success'):
            self.logger.error(f"Play failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Check if trick was won
        if result.get('trickWinner') is not None:
            winner_idx = result['trickWinner']
            winner = game.players[winner_idx]
            points = result.get('trickPoints', 0)
            self.logger.trick_winner(winner_idx, winner.name, winner.team, points)
        
        # Check if round ended
        if result.get('roundEnd'):
            us_score = game.team_scores['us']
            them_score = game.team_scores['them']
            winner = 'us' if us_score > them_score else 'them' if them_score > us_score else 'tie'
            self.logger.round_end(us_score, them_score, winner)
            self.stats['total_rounds'] += 1
        
        return True
    
    def run_interactive_game(self):
        """Run an interactive game with manual input"""
        self.logger.header("INTERACTIVE MODE")
        self.logger.info("You can manually control Player 0, others are bots", LogLevel.NORMAL)
        
        # Create game
        game = self.create_game()
        game.players[0].is_bot = False  # Make player 0 human
        game.players[0].name = "You"
        
        # Start game
        if not game.start_game():
            self.logger.error("Failed to start game")
            return False
        
        self.logger.game_start(game.room_id, game.dealer_index)
        
        # Game loop
        round_count = 0
        
        while game.phase not in [GamePhase.FINISHED.value, GamePhase.GAMEOVER.value]:
            current_player = game.players[game.current_turn]
            
            # Display game state
            print("\n" + "="*60)
            self.logger.display_game_state(game.get_game_state())
            
            if current_player.index == 0:
                # Human player's turn
                self.logger.display_player_hand(0, current_player.hand)
                
                if game.phase == GamePhase.BIDDING.value:
                    self._interactive_bid(game, current_player)
                elif game.phase == GamePhase.PLAYING.value:
                    self._interactive_play(game, current_player)
            else:
                # Bot turn
                input(f"\nPress Enter to see {current_player.name}'s turn...")
                
                if game.phase == GamePhase.BIDDING.value:
                    self._handle_bidding_turn(game, current_player)
                elif game.phase == GamePhase.PLAYING.value:
                    self._handle_playing_turn(game, current_player)
            
            round_count += 1
        
        # Game ended
        self.logger.game_over(
            'us' if game.match_scores['us'] > game.match_scores['them'] else 'them',
            game.match_scores['us'],
            game.match_scores['them']
        )
        
        return True
    
    def _interactive_bid(self, game: Game, player):
        """Handle interactive bidding"""
        print("\nYour turn to bid!")
        print("Options: SUN, HOKUM [suit], ASHKAL, PASS")
        
        while True:
            bid_input = input("Enter your bid: ").strip().upper()
            
            if bid_input == 'PASS':
                result = game.handle_bid(player.index, 'PASS')
                if result.get('success'):
                    self.logger.bid_action(player.index, player.name, 'PASS')
                    break
                else:
                    self.logger.error(f"Bid failed: {result.get('error')}")
            
            elif bid_input == 'SUN':
                result = game.handle_bid(player.index, 'SUN')
                if result.get('success'):
                    self.logger.bid_action(player.index, player.name, 'SUN')
                    break
                else:
                    self.logger.error(f"Bid failed: {result.get('error')}")
            
            elif bid_input == 'ASHKAL':
                result = game.handle_bid(player.index, 'ASHKAL')
                if result.get('success'):
                    self.logger.bid_action(player.index, player.name, 'ASHKAL')
                    break
                else:
                    self.logger.error(f"Bid failed: {result.get('error')}")
            
            elif bid_input.startswith('HOKUM'):
                parts = bid_input.split()
                if len(parts) == 2:
                    suit = parts[1]
                    result = game.handle_bid(player.index, 'HOKUM', suit)
                    if result.get('success'):
                        self.logger.bid_action(player.index, player.name, 'HOKUM', suit)
                        break
                    else:
                        self.logger.error(f"Bid failed: {result.get('error')}")
                else:
                    print("Usage: HOKUM [S/H/D/C]")
            
            else:
                print("Invalid bid. Try again.")
    
    def _interactive_play(self, game: Game, player):
        """Handle interactive card play"""
        print("\nYour turn to play!")
        print("Your hand:")
        for i, card in enumerate(player.hand):
            print(f"  {i}: {card['rank']}{card['suit']}")
        
        while True:
            try:
                card_input = input("Enter card index to play: ").strip()
                card_index = int(card_input)
                
                if 0 <= card_index < len(player.hand):
                    card = player.hand[card_index]
                    result = game.play_card(player.index, card_index)
                    
                    if result.get('success'):
                        self.logger.play_card(player.index, player.name, card, card_index)
                        
                        if result.get('trickWinner') is not None:
                            winner_idx = result['trickWinner']
                            winner = game.players[winner_idx]
                            points = result.get('trickPoints', 0)
                            self.logger.trick_winner(winner_idx, winner.name, winner.team, points)
                        
                        break
                    else:
                        self.logger.error(f"Play failed: {result.get('error')}")
                else:
                    print(f"Invalid index. Choose 0-{len(player.hand)-1}")
            
            except ValueError:
                print("Please enter a number")
    
    def print_stats(self):
        """Print test statistics"""
        self.logger.header("TEST STATISTICS")
        self.logger.info(f"Games Played: {self.stats['games_played']}", LogLevel.QUIET)
        self.logger.info(f"Games Completed: {self.stats['games_completed']}", LogLevel.QUIET)
        self.logger.info(f"Games Failed: {self.stats['games_failed']}", LogLevel.QUIET)
        self.logger.info(f"Us Wins: {self.stats['us_wins']}", LogLevel.QUIET)
        self.logger.info(f"Them Wins: {self.stats['them_wins']}", LogLevel.QUIET)
        self.logger.info(f"Total Rounds: {self.stats['total_rounds']}", LogLevel.QUIET)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="CLI Test Runner for Baloot Game",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python cli_test_runner.py --interactive

  # Run full game scenario
  python cli_test_runner.py --scenario full_game --verbose

  # Run 10 games for stress testing
  python cli_test_runner.py --scenario stress_test --games 10

  # Save logs to file
  python cli_test_runner.py --scenario full_game --log-file test.log --debug
        """
    )
    
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Run in interactive mode (manual control)')
    
    parser.add_argument('--scenario', '-s', type=str,
                        help='Run a specific test scenario')
    
    parser.add_argument('--list-scenarios', '-l', action='store_true',
                        help='List all available scenarios')
    
    parser.add_argument('--games', '-g', type=int, default=1,
                        help='Number of games to run (default: 1)')
    
    parser.add_argument('--log-file', '-f', type=str,
                        help='Save logs to file')
    
    # Logging levels (mutually exclusive)
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument('--quiet', '-q', action='store_true',
                          help='Quiet mode (minimal output)')
    log_group.add_argument('--verbose', '-v', action='store_true',
                          help='Verbose mode (detailed output)')
    log_group.add_argument('--debug', '-d', action='store_true',
                          help='Debug mode (full game state dumps)')
    
    args = parser.parse_args()
    
    # List scenarios
    if args.list_scenarios:
        print("\nAvailable Test Scenarios:")
        print("=" * 60)
        for name in list_scenarios():
            info = get_scenario_info(name)
            if info:
                print(f"\n{name}")
                print(f"  {info['description']}")
        print()
        return 0
    
    # Determine log level
    if args.quiet:
        log_level = LogLevel.QUIET
    elif args.verbose:
        log_level = LogLevel.VERBOSE
    elif args.debug:
        log_level = LogLevel.DEBUG
    else:
        log_level = LogLevel.NORMAL
    
    # Create logger
    logger = GameLogger(level=log_level, log_file=args.log_file)
    
    # Create test runner
    runner = CLITestRunner(logger)
    
    # Run tests
    try:
        if args.interactive:
            # Interactive mode
            runner.run_interactive_game()
        
        else:
            # Automated mode
            scenario = args.scenario or 'full_game'
            
            logger.header(f"CLI TEST RUNNER - Running {args.games} game(s)")
            
            start_time = time.time()
            
            for i in range(args.games):
                if args.games > 1:
                    logger.subheader(f"Game {i+1}/{args.games}")
                
                success = runner.run_automated_game(scenario)
                
                if not success:
                    logger.error(f"Game {i+1} failed")
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # Print statistics
            runner.print_stats()
            
            logger.info(f"Total Time: {elapsed:.2f}s", LogLevel.QUIET)
            if runner.stats['games_completed'] > 0:
                avg_time = elapsed / runner.stats['games_completed']
                logger.info(f"Average Time per Game: {avg_time:.2f}s", LogLevel.QUIET)
                logger.info(f"Games per Second: {runner.stats['games_completed']/elapsed:.2f}", LogLevel.QUIET)
    
    except KeyboardInterrupt:
        logger.warning("\nTest interrupted by user")
        runner.print_stats()
        return 1
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
