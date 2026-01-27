
import logging
from ai_worker.strategies.bidding import BiddingStrategy
from ai_worker.bot_context import BotContext
from game_engine.models.card import Card

# Mock Game State
game_state = {
    'players': [
        {'name': 'Bot', 'hand': [{'suit': '♥', 'rank': 'A'}, {'suit': '♠', 'rank': 'K'}], 'position': 'Bottom', 'team': 'us'}
    ],
    'phase': 'BIDDING',
    'biddingPhase': 'ROUND_1',
    'floorCard': {'suit': '♦', 'rank': '7'},
    'dealerIndex': 0,
    'biddingRound': 1,
    'matchScores': {'us': 0, 'them': 0},
    'tableCards': []
}

ctx = BotContext(game_state, 0)
strategy = BiddingStrategy()

print("Running Strategy...")
try:
    decision = strategy.get_decision(ctx)
    print("Decision:", decision)
except Exception as e:
    import traceback
    traceback.print_exc()
