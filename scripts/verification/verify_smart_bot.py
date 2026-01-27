
import sys
import os
import logging

# Setup Path
sys.path.append(os.getcwd())

from ai_worker.agent import BotAgent
from game_engine.models.card import Card
from ai_worker.bot_context import BotContext

def test_smart_sahn():
    print("\n--- TEST: SMART SAHN (HOKUM) ---")
    agent = BotAgent()
    
    # Scene: I am Player 0 (Bottom), Bidder = Bottom. Mode = HOKUM.
    # Hand: High Trumps (J, 9, A) and some others.
    # Opponents: Have Trumps?
    
    # Case 1: Opponents have trumps -> SHOULD Sahn (Lead Trump)
    game_state_1 = {
        'players': [
            {'name': 'Bot', 'position': 'Bottom', 'team': 'us', 'hand': [{'rank': 'J', 'suit': '♠'}, {'rank': '9', 'suit': '♠'}, {'rank': 'A', 'suit': '♥'}]},
            {'name': 'Right', 'position': 'Right', 'team': 'them', 'hand': []},
            {'name': 'Top', 'position': 'Top', 'team': 'us', 'hand': []},
            {'name': 'Left', 'position': 'Left', 'team': 'them', 'hand': []}
        ],
        'phase': 'PLAYING',
        'gameMode': 'HOKUM',
        'trumpSuit': '♠',
        'dealerIndex': 1,
        'currentRoundTricks': [], # No tricks played yet
        'bid': {'type': 'HOKUM', 'suit': '♠', 'bidder': 'Bottom'},
        'tableCards': []
    }
    
    decision = agent.get_decision(game_state_1, 0)
    print(f"Case 1 (Fresh Game): {decision}")
    
    if decision['action'] == 'PLAY' and decision['cardIndex'] in [0, 1]: # J or 9
         print("SUCCESS: Bot leads Trump (Sahn).")
    else:
         print(f"FAILURE: Bot did not lead trump. {decision}")

    # Case 2: Enemies are VOID in Trumps -> Should NOT Sahn (waste trumps)
    # How to simulate? Add past tricks where enemies did not follow trump lead.
    
    print("\n--- TEST: SMART SAHN (AVOID BLEEDING) ---")
    # Trick 1: Bottom Led 7♠ (Trump), Right Played ♠, Top Played ♠, Left Played ♥ (VOID!)
    # Trick 2: Bottom Led 8♠ (Trump), Right Played ♦ (VOID!), Top Played ♠, Left Played ♦ (Still Void)
    # So Right and Left are Void in ♠.
    
    trick_1 = {
        'winner': 'Bottom', 
        'cards': [
            {'rank': '7', 'suit': '♠', 'playedBy': 'Bottom'},
            {'rank': 'K', 'suit': '♥', 'playedBy': 'Right'}, # VOID IN SPADES
            {'rank': '8', 'suit': '♠', 'playedBy': 'Top'},
            {'rank': 'Q', 'suit': '♦', 'playedBy': 'Left'} # VOID IN SPADES
        ]
    }
    
    game_state_2 = game_state_1.copy()
    game_state_2['currentRoundTricks'] = [trick_1]
    
    # Now Bot has J, 9. 
    # Should it lead J♠? No, enemies are void. Playing J♠ just wastes it (unless to draw partner... but assume simple logic first).
    # Logic typically says: "Did I buy it? Yes. Should I open? Only if enemies have trumps."
    # Enemies (Left, Right) both showed void in trick 1.
    
    decision_2 = agent.get_decision(game_state_2, 0)
    print(f"Case 2 (Enemies Void): {decision_2}")
    
    # It should probably lead the Ace of Hearts (Index 2) or something else.
    if decision_2['action'] == 'PLAY' and decision_2['cardIndex'] == 2: # Ace Hearts
         print("SUCCESS: Bot switched to Non-Trump lead.")
    else:
         print(f"FAILURE: Bot persisted in leading trump? {decision_2}")


def test_void_avoidance():
    print("\n--- TEST: VOID AVOIDANCE ---")
    agent = BotAgent()
    
    # Scene: I have K♥. Left is Void in ♥. Mode = Hokum.
    # Leading K♥ is suicide (Left will cut).
    
    game_state = {
        'players': [
            {'name': 'Bot', 'position': 'Bottom', 'team': 'us', 'hand': [{'rank': 'K', 'suit': '♥'}, {'rank': '7', 'suit': '♣'}]},
            {'name': 'Right', 'position': 'Right', 'team': 'them', 'hand': []},
            {'name': 'Top', 'position': 'Top', 'team': 'us', 'hand': []},
            {'name': 'Left', 'position': 'Left', 'team': 'them', 'hand': []}
        ],
        'phase': 'PLAYING',
        'gameMode': 'HOKUM',
        'trumpSuit': '♠',
        'currentRoundTricks': [
             {
                  'winner': 'Top',
                  'cards': [
                       {'rank': 'A', 'suit': '♥', 'playedBy': 'Top'},
                       {'rank': '9', 'suit': '♣', 'playedBy': 'Left'}, # Left Void in ♥!
                       {'rank': '7', 'suit': '♥', 'playedBy': 'Bottom'},
                       {'rank': '8', 'suit': '♥', 'playedBy': 'Right'}
                  ]
             }
        ],
        'bid': {'type': 'HOKUM', 'suit': '♠', 'bidder': 'Right'}, # Enemy bid
        'tableCards': [],
        'dealerIndex': 1 # Ensure dealer index is set
    }
    
    decision = agent.get_decision(game_state, 0)
    print(f"Void Case: {decision}")
    
    if decision['action'] == 'PLAY':
         # Index 0 is K♥ (Dangerous). Index 1 is 7♣ (Safe).
         if decision['cardIndex'] == 1:
              print("SUCCESS: Bot avoided leading into Void (Void Avoidance).")
         elif decision['cardIndex'] == 0:
              print("FAILURE: Bot led K♥ despite Left being void!")

if __name__ == "__main__":
    test_smart_sahn()
    test_void_avoidance()
