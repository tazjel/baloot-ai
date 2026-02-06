import pytest
from unittest.mock import MagicMock
from ai_worker.agent import bot_agent
from ai_worker.memory import CardMemory

def test_bot_detects_contradiction():
    # Setup state
    # Round history: Trick 1
    # P1 (Bottom) led Spades. P2 (Right) followed. P3 (Top) played Hearts (Void Spades). P4 (Left) followed.

    trick1 = {
        'cards': [
            {'rank': 'K', 'suit': '♠', 'playedBy': 'Bottom'},
            {'rank': '7', 'suit': '♠', 'playedBy': 'Right'},
            {'rank': '7', 'suit': '♥', 'playedBy': 'Top'}, # Void Spade!
            {'rank': '8', 'suit': '♠', 'playedBy': 'Left'}
        ]
    }

    # Now P3 (Top) plays Spade in current trick (Table)
    # Current table: P2 led Diamonds. P3 plays Spade.

    table_cards = [
        {'card': {'rank': 'Q', 'suit': '♦'}, 'playedBy': 'Right', 'playerId': 'p2'},
        {'card': {'rank': '9', 'suit': '♠'}, 'playedBy': 'Top', 'playerId': 'p3'} # Contradiction! Played Spade but void previously.
    ]

    game_state = {
        'gameId': 'game1',
        'currentRoundTricks': [trick1],
        'tableCards': table_cards,
        'trumpSuit': '♦',
        'gameMode': 'SUN',
        'phase': 'PLAYING',
        'players': [
            {'position': 'Bottom', 'strategy': 'heuristic'},
            {'position': 'Right', 'strategy': 'heuristic'},
            {'position': 'Top', 'strategy': 'heuristic'},
            {'position': 'Left', 'strategy': 'heuristic'}
        ],
        'matchScores': {'us': 0, 'them': 0},
        'qaydState': {'active': False},
        'strictMode': False
    }

    # Bot is observing (say, P1 or P4, or even P2).
    # Let's say Bot is P4 (Left). Index 3.
    # Player indices: Bottom=0, Right=1, Top=2, Left=3.

    # We need to ensure BotAgent memory is reset or handled.
    # The get_decision method should handle reset if gameId changes.
    bot_agent.current_game_id = None

    # We need to mock BotContext or ensure it works with the dict provided.
    # BotContext extracts info from game_state.
    # BotContext initialization: BotContext(game_state, player_index)
    # It accesses game_state['players'][player_index]['hand'] usually?
    # Let's check BotContext to see if it requires 'hand' in game_state['players'] or separate.
    # Assuming BotContext is robust or we provide enough data.

    # Add hands to players to avoid KeyError
    for p in game_state['players']:
        p['hand'] = []

    # Add 'bid' to raw_state/game_state as expected by BotAgent logic
    game_state['bid'] = {}

    decision = bot_agent.get_decision(game_state, 3)

    print(decision)

    assert decision['action'] == 'QAYD_ACCUSATION'
    assert decision['accusation']['violation_type'] == 'REVOKE'
    assert decision['accusation']['crime_card']['suit'] == '♠'
    assert decision['accusation']['crime_card']['rank'] == '9'
