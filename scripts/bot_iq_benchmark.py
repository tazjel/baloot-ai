"""
Bot IQ Benchmark — Measures AI Playing Strength
=================================================
Runs N headless games with 4 AI bots and collects statistics:
  - Win rates per team
  - Average scores
  - Decision reasoning breakdown
  - Points per trick efficiency
  - Game duration (tricks to finish)

Usage:
  python scripts/bot_iq_benchmark.py          # 10 games (quick)
  python scripts/bot_iq_benchmark.py --games 50  # 50 games (thorough)
  python scripts/bot_iq_benchmark.py --games 100 --verbose  # detailed output
"""

import sys
import os
import time
import random
import argparse
import logging
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_engine.logic.game import Game
from game_engine.models.constants import GamePhase
from ai_worker.bot_context import BotContext
from ai_worker.strategies.bidding import BiddingStrategy
from ai_worker.strategies.playing import PlayingStrategy

import contextlib
import io

# Suppress noisy logs during benchmarking
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger("benchmark")
logger.setLevel(logging.INFO)

# Silence game engine and AI worker noise
for noisy in ['GameServer', 'game_engine', 'ai_worker', 'server', 
              'ai_worker.strategies', 'ai_worker.mcts', '__main__']:
    logging.getLogger(noisy).setLevel(logging.CRITICAL)

# ═══════════════════════════════════════════════════
#  Stats Collector
# ═══════════════════════════════════════════════════

class BenchmarkStats:
    def __init__(self):
        self.games_played = 0
        self.games_completed = 0
        self.games_crashed = 0
        self.wins = {'us': 0, 'them': 0, 'draw': 0}
        self.total_scores = {'us': 0, 'them': 0}
        self.round_scores = {'us': [], 'them': []}
        self.tricks_per_game = []
        self.rounds_per_game = []
        self.reasoning_counts = defaultdict(int)
        self.bid_types = defaultdict(int)
        self.game_durations = []  # seconds
        self.endgame_solver_hits = 0
        self.finesse_count = 0
        self.point_protection_count = 0
        self.cross_ruff_count = 0
        self.smart_trump_count = 0

    def record_reasoning(self, reasoning: str):
        """Track AI decision types."""
        self.reasoning_counts[reasoning] += 1
        r = reasoning.lower()
        if 'endgame' in r:
            self.endgame_solver_hits += 1
        if 'finesse' in r:
            self.finesse_count += 1
        if 'point protection' in r:
            self.point_protection_count += 1
        if 'cross-ruff' in r or 'ruff' in r:
            self.cross_ruff_count += 1
        if 'smart trump' in r or 'cheap trump' in r:
            self.smart_trump_count += 1

    def print_report(self):
        """Print the full benchmark report."""
        print("\n" + "═" * 60)
        print("  🧠 BOT IQ BENCHMARK REPORT")
        print("═" * 60)

        # --- GAME RESULTS ---
        print(f"\n📊 Games Played:    {self.games_played}")
        print(f"   ✅ Completed:    {self.games_completed}")
        print(f"   ❌ Crashed:      {self.games_crashed}")

        if self.games_completed > 0:
            print(f"\n🏆 Win Rate:")
            total = self.games_completed
            print(f"   Team US:   {self.wins['us']:>3}/{total} ({100*self.wins['us']/total:.1f}%)")
            print(f"   Team THEM: {self.wins['them']:>3}/{total} ({100*self.wins['them']/total:.1f}%)")

            avg_us = self.total_scores['us'] / total
            avg_them = self.total_scores['them'] / total
            print(f"\n📈 Average Match Score:")
            print(f"   Team US:   {avg_us:.1f}")
            print(f"   Team THEM: {avg_them:.1f}")

        if self.tricks_per_game:
            avg_tricks = sum(self.tricks_per_game) / len(self.tricks_per_game)
            print(f"\n⏱️ Average Tricks/Game: {avg_tricks:.1f}")

        if self.rounds_per_game:
            avg_rounds = sum(self.rounds_per_game) / len(self.rounds_per_game)
            print(f"   Average Rounds/Game: {avg_rounds:.1f}")

        if self.game_durations:
            avg_dur = sum(self.game_durations) / len(self.game_durations)
            print(f"   Average Duration:    {avg_dur:.2f}s")

        # --- AI INTELLIGENCE METRICS ---
        print(f"\n🧠 AI Intelligence Metrics:")
        total_decisions = sum(self.reasoning_counts.values())
        if total_decisions > 0:
            print(f"   Total Decisions:      {total_decisions}")
            print(f"   Endgame Solver Hits:  {self.endgame_solver_hits}")
            print(f"   Finesse Plays:        {self.finesse_count}")
            print(f"   Point Protections:    {self.point_protection_count}")
            print(f"   Smart Trump Saves:    {self.smart_trump_count}")

        # --- TOP REASONING ---
        if self.reasoning_counts:
            print(f"\n📋 Top 15 Decision Types:")
            sorted_reasons = sorted(self.reasoning_counts.items(), key=lambda x: -x[1])
            for reason, count in sorted_reasons[:15]:
                pct = 100 * count / total_decisions if total_decisions else 0
                bar = "█" * int(pct / 2)
                print(f"   {reason[:40]:<40} {count:>4} ({pct:5.1f}%) {bar}")

        # --- BID TYPES ---
        if self.bid_types:
            print(f"\n🃏 Bidding Distribution:")
            total_bids = sum(self.bid_types.values())
            for bid, count in sorted(self.bid_types.items(), key=lambda x: -x[1]):
                pct = 100 * count / total_bids
                print(f"   {bid:<15} {count:>4} ({pct:5.1f}%)")

        # --- IQ SCORE ---
        print(f"\n{'═' * 60}")
        iq = self._calculate_iq()
        print(f"  🎯 BOT IQ SCORE: {iq}/100")
        print(f"{'═' * 60}\n")

    def _calculate_iq(self):
        """Calculate a composite IQ score 0-100."""
        score = 0
        total_decisions = sum(self.reasoning_counts.values())
        if total_decisions == 0:
            return 0

        # Completion rate (10 pts)
        if self.games_played > 0:
            score += 10 * (self.games_completed / self.games_played)

        # Decision diversity — using multiple strategies (20 pts)
        unique_strategies = len(self.reasoning_counts)
        score += min(20, unique_strategies * 2)

        # Finesse rate — sign of intelligence (20 pts)
        finesse_rate = self.finesse_count / total_decisions
        score += min(20, finesse_rate * 200)

        # Point protection (15 pts)
        pp_rate = self.point_protection_count / total_decisions
        score += min(15, pp_rate * 150)

        # Endgame solver usage (15 pts)
        eg_rate = self.endgame_solver_hits / total_decisions
        score += min(15, eg_rate * 150)

        # Smart trumping (10 pts)
        st_rate = self.smart_trump_count / total_decisions
        score += min(10, st_rate * 100)

        # No crashes bonus (10 pts)
        if self.games_crashed == 0:
            score += 10

        return int(min(100, score))


# ═══════════════════════════════════════════════════
#  Headless Game Runner
# ═══════════════════════════════════════════════════

class HeadlessGameRunner:
    """Runs a single complete Baloot match (multiple rounds until 152+ points)."""

    def __init__(self, stats: BenchmarkStats, verbose=False):
        self.stats = stats
        self.verbose = verbose
        self.bidding_strategy = BiddingStrategy()
        self.playing_strategy = PlayingStrategy()
        self.total_tricks = 0
        self.total_rounds = 0

    def run_game(self, game_id: int) -> dict:
        """Run a single complete match. Returns result dict."""
        game = Game(f"benchmark_{game_id}")

        # Add 4 bot players
        for i in range(4):
            game.add_player(f"bot_{i}", f"Bot {i}")

        if not game.start_game():
            return {'success': False, 'error': 'Failed to start'}

        max_iterations = 5000  # Safety limit per match (multi-round)
        iteration = 0

        while game.phase != GamePhase.GAMEOVER.value and iteration < max_iterations:
            iteration += 1
            try:
                # Handle round-end: start a new round
                if game.phase == GamePhase.FINISHED.value:
                    self.total_rounds += 1
                    self._start_new_round(game)
                    continue

                result = self._step(game)
                if result and not result.get('success', True):
                    if self.verbose:
                        print(f"  ⚠️ Step error: {result.get('error', 'unknown')}")
                    if not self._force_recovery(game):
                        return {'success': False, 'error': result.get('error')}
            except Exception as e:
                if self.verbose:
                    import traceback
                    traceback.print_exc()
                return {'success': False, 'error': str(e)}

        if game.phase == GamePhase.GAMEOVER.value:
            scores = game.match_scores
            winner = 'us' if scores['us'] > scores['them'] else ('them' if scores['them'] > scores['us'] else 'draw')
            return {
                'success': True,
                'winner': winner,
                'scores': scores,
                'tricks': self.total_tricks,
                'rounds': self.total_rounds
            }
        else:
            return {'success': False, 'error': f'Max iterations reached ({max_iterations})'}

    def _start_new_round(self, game: Game):
        """Start a new round within the same match."""
        game.reset_round_state()
        game.deal_initial_cards()
        game.phase = GamePhase.BIDDING.value
        from game_engine.logic.bidding_engine import BiddingEngine
        game.bidding_engine = BiddingEngine(
            dealer_index=game.dealer_index,
            floor_card=game._floor_card_obj,
            players=game.players,
            match_scores=game.match_scores,
        )
        game.current_turn = game.bidding_engine.current_turn

    def _step(self, game: Game) -> dict:
        """Execute one step of the game (one bid or one card play)."""
        current_idx = game.current_turn
        if current_idx is None or current_idx < 0 or current_idx >= len(game.players):
            return {'success': False, 'error': f'Invalid turn index: {current_idx}'}

        if game.phase == GamePhase.BIDDING.value:
            return self._handle_bidding(game, current_idx)
        elif game.phase == GamePhase.PLAYING.value:
            return self._handle_playing(game, current_idx)
        elif game.phase == GamePhase.DOUBLING.value:
            # Skip doubling — just pass
            try:
                return game.handle_double(current_idx)
            except:
                game.phase = GamePhase.PLAYING.value
                return {'success': True}
        elif game.phase == GamePhase.VARIANT_SELECTION.value:
            # Auto-select open variant
            try:
                game_state = game.get_game_state()
                ctx = BotContext(game_state, current_idx)
                with contextlib.redirect_stdout(io.StringIO()):
                    decision = self.bidding_strategy.get_variant_decision(ctx)
                variant = decision.get('variant', 'OPEN')
                if hasattr(game, 'handle_variant_selection'):
                    return game.handle_variant_selection(current_idx, variant)
                else:
                    game.phase = GamePhase.PLAYING.value
                    return {'success': True}
            except:
                game.phase = GamePhase.PLAYING.value
                return {'success': True}
        elif game.phase == GamePhase.CHALLENGE.value:
            # Auto-cancel any challenge
            try:
                game.handle_qayd_cancel()
            except:
                pass
            return {'success': True}
        elif game.phase in [GamePhase.FINISHED.value, GamePhase.GAMEOVER.value]:
            return {'success': True, 'finished': True}
        else:
            return {'success': True}

    def _handle_bidding(self, game: Game, player_idx: int) -> dict:
        """Get AI bidding decision and execute it."""
        try:
            # Detect dead bidding engine (all pass scenario)
            if game.bidding_engine and game.bidding_engine.phase.value == 'FINISHED':
                # All pass — bidding engine is done but Game is still BIDDING
                # This happens when the game auto-redeals but doesn't create new engine
                self._start_new_round(game)
                return {'success': True}

            game_state = game.get_game_state()
            ctx = BotContext(game_state, player_idx)

            with contextlib.redirect_stdout(io.StringIO()):
                decision = self.bidding_strategy.get_decision(ctx)
            action = decision.get('action', 'PASS')
            suit = decision.get('suit')

            self.stats.bid_types[action] += 1

            if action == 'SUN':
                return game.handle_bid(player_idx, 'SUN')
            elif action == 'HOKUM' and suit:
                return game.handle_bid(player_idx, 'HOKUM', suit=suit)
            else:
                return game.handle_bid(player_idx, 'PASS')
        except Exception as e:
            # Fallback to PASS
            return game.handle_bid(player_idx, 'PASS')

    def _handle_playing(self, game: Game, player_idx: int) -> dict:
        """Get AI playing decision and execute it."""
        try:
            game_state = game.get_game_state()
            ctx = BotContext(game_state, player_idx)
            ctx.use_mcts = False  # Use pure heuristics for speed (no MCTS in benchmark)

            with contextlib.redirect_stdout(io.StringIO()):
                decision = self.playing_strategy.get_decision(ctx)

            card_idx = decision.get('cardIndex', 0)
            reasoning = decision.get('reasoning', 'Unknown')

            self.stats.record_reasoning(reasoning)

            if self.verbose:
                player = game.players[player_idx]
                if card_idx < len(player.hand):
                    card = player.hand[card_idx]
                    print(f"  [{player.name}] plays {card} — {reasoning}")

            result = game.play_card(player_idx, card_idx)

            # Track trick completion
            if result.get('success'):
                if result.get('trickComplete') or len(game.table_cards) == 0:
                    self.total_tricks += 1
                if result.get('roundComplete'):
                    self.total_rounds += 1

            return result
        except Exception as e:
            # Fallback: play first legal card
            player = game.players[player_idx]
            for idx, card in enumerate(player.hand):
                if game.is_valid_move(card, player.hand):
                    return game.play_card(player_idx, idx)
            return {'success': False, 'error': f'No valid moves: {e}'}

    def _force_recovery(self, game: Game) -> bool:
        """Try to recover from a stuck state."""
        try:
            if game.phase == GamePhase.BIDDING.value:
                # Force everyone to pass until bidding resolves
                for _ in range(8):  # Max bidding rounds
                    if game.phase != GamePhase.BIDDING.value:
                        return True
                    game.handle_bid(game.current_turn, 'PASS')
                return game.phase != GamePhase.BIDDING.value

            elif game.phase == GamePhase.PLAYING.value:
                # Force play first valid card
                player = game.players[game.current_turn]
                for idx, card in enumerate(player.hand):
                    if game.is_valid_move(card, player.hand):
                        game.play_card(game.current_turn, idx)
                        return True
            return False
        except:
            return False


# ═══════════════════════════════════════════════════
#  Main Entry Point
# ═══════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Bot IQ Benchmark')
    parser.add_argument('--games', type=int, default=10, help='Number of games to simulate')
    parser.add_argument('--verbose', action='store_true', help='Show per-move output')
    args = parser.parse_args()

    num_games = args.games
    verbose = args.verbose

    print("═" * 60)
    print("  🧠 BOT IQ BENCHMARK")
    print(f"  Running {num_games} headless games...")
    print("═" * 60)

    stats = BenchmarkStats()
    total_start = time.time()

    for i in range(num_games):
        stats.games_played += 1
        game_start = time.time()

        if verbose:
            print(f"\n{'─' * 40}")
            print(f"  Game {i+1}/{num_games}")
            print(f"{'─' * 40}")

        runner = HeadlessGameRunner(stats, verbose=verbose)
        result = runner.run_game(i)

        game_dur = time.time() - game_start
        stats.game_durations.append(game_dur)

        if result.get('success'):
            stats.games_completed += 1
            stats.wins[result['winner']] += 1
            stats.total_scores['us'] += result['scores']['us']
            stats.total_scores['them'] += result['scores']['them']
            stats.tricks_per_game.append(result.get('tricks', 0))
            stats.rounds_per_game.append(result.get('rounds', 0))

            if not verbose:
                winner_emoji = "🟢" if result['winner'] == 'us' else "🔴" if result['winner'] == 'them' else "⚪"
                scores = result['scores']
                print(f"  {winner_emoji} Game {i+1:>3}: {scores['us']:>3} - {scores['them']:<3}  "
                      f"({result.get('rounds', '?')} rounds, {game_dur:.2f}s)")
        else:
            stats.games_crashed += 1
            print(f"  ❌ Game {i+1:>3}: CRASHED — {result.get('error', 'unknown')[:50]}")

    total_dur = time.time() - total_start
    print(f"\n⏱️ Total benchmark time: {total_dur:.1f}s")

    stats.print_report()


if __name__ == "__main__":
    main()
