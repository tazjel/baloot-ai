import sys
import os
import traceback

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_worker.agent import ai_worker.agent
from game_logic import Game, Player, Card

class MockGame:
    def __init__(self):
        self.players = []
        self.table_cards = []
        self.trump_suit = None
        self.game_mode = None
        self.bid = {'type': None, 'bidder': None}
        self.team_scores = {'us': 0, 'them': 0}
        self.floor_card = None
        self.phase = 'PLAYING'
        self.current_turn = 0
        self.dealer_index = 0
        self.round_history = [] # For history checking

    def get_game_state(self):
        return {
            "phase": self.phase,
            "players": [p.to_dict() for p in self.players],
            "tableCards": [{"playerId": tc['playerId'], "card": tc['card'].to_dict(), "playedBy": tc['playedBy']} for tc in self.table_cards],
            "gameMode": self.game_mode,
            "trumpSuit": self.trump_suit,
            "bid": self.bid,
            "teamScores": self.team_scores,
            "floorCard": self.floor_card.to_dict() if self.floor_card else None,
            "dealerIndex": self.dealer_index,
            "currentTurnIndex": self.current_turn,
            "roundHistory": self.round_history
        }

def create_card(rank, suit):
    suit_map = {'H': '♥', 'S': '♠', 'D': '♦', 'C': '♣'}
    real_suit = suit_map.get(suit, suit)
    return Card(real_suit, rank)

def setup_game_scenario(my_hand_str, table_cards_str=None, mode='SUN', trump=None, my_index=0):
    game = MockGame()
    game.game_mode = mode
    game.trump_suit = trump
    
    # Create Players
    for i in range(4):
        p = Player(f"p{i}", f"Player {i}", i, game)
        game.players.append(p)
        
    # Set My Hand
    # Format "AH KS ..."
    my_hand = []
    if my_hand_str:
        for cs in my_hand_str.split():
            rank = cs[:-1]
            suit = cs[-1]
            my_hand.append(create_card(rank, suit))
    game.players[my_index].hand = my_hand
    
    # Set Table
    # Format "AH(Right) KS(Top)..." - playedBy is important for partnership logic
    if table_cards_str:
        parts = table_cards_str.split()
        for p in parts:
            # Parse card and player
            # e.g. AH(Right)
            card_part = p.split('(')[0]
            pos_part = p.split('(')[1].replace(')', '')
            
            rank = card_part[:-1]
            suit = card_part[-1]
            
            # Find player by position
            # 0=Bottom, 1=Right, 2=Top, 3=Left
            pos_map = {'Bottom': 0, 'Right': 1, 'Top': 2, 'Left': 3}
            p_idx = pos_map.get(pos_part, 0)
            
            game.table_cards.append({
                "playerId": game.players[p_idx].id,
                "card": create_card(rank, suit),
                "playedBy": pos_part
            })
            
    return game

def test_bidding_strong_sun():
    # Hand with Aces and 10s should bid Sun
    game = setup_game_scenario("A♠ 10♠ K♠ A♥ 10♥", mode=None)
    game.phase = 'BIDDING'
    game.floor_card = create_card('7', '♦') # Irrelevant floor
    
    decision = bot_agent.get_decision(game.get_game_state(), 0)
    assert decision['action'] in ['SUN', 'ASHKAL'] # Ashkal if dealer logic calls for it, but SUN is safe bet

def test_play_partner_winning():
    # Partner (Top) played Ace of Hearts. We (Bottom) have 10 of Hearts.
    # We should throw the 10 (Score) because partner is winning.
    game = setup_game_scenario("10♥ 7♥ 8♦", "A♥(Top) 7♣(Right)", mode='SUN', my_index=0)
    
    decision = bot_agent.get_decision(game.get_game_state(), 0)
    
    # We must play 10H to give points
    target_card = next(c for c in game.players[0].hand if c.rank == '10' and c.suit == '♥')
    idx = game.players[0].hand.index(target_card)
    
    assert decision['action'] == 'PLAY'
    assert decision['cardIndex'] == idx

def test_play_cut_opponent():
    # Opponent (Right) played Ace Hearts (11 pts).
    # Game is Hokum. Trump is Spades.
    # We have no Hearts. We have Spades (7, 8).
    # We must Cut with Spade.
    
    game = setup_game_scenario("7♠ 8♠ 9♦", "A♥(Right)", mode='HOKUM', trump='♠', my_index=0)
    
    decision = bot_agent.get_decision(game.get_game_state(), 0)
    
    # Should play a Spade
    card_idx = decision['cardIndex']
    played_card = game.players[0].hand[card_idx]
    
    assert played_card.suit == '♠' 

def test_lead_strongest():
    # We are leading. We have Ace Spades. We should play it in SUN.
    game = setup_game_scenario("A♠ 7♥ 8♦", "", mode='SUN', my_index=0)
    
    decision = bot_agent.get_decision(game.get_game_state(), 0)
    
    card_idx = decision['cardIndex']
    played_card = game.players[0].hand[card_idx]
    
    # Ideally plays Ace
    assert played_card.rank == 'A' and played_card.suit == '♠'


def test_bid_with_sira():
    # Hand: A, K, Q of Hearts (Sira), 7 Spades, 8 Clubs.
    # Score: A(10) + K(3) + Q(2) = 15. 
    # Plus Sira (Hearts) = +5. Total 20. Should Bid SUN (threshold 20).
    bot = bot_agent
    game_state = {
        'phase': 'BIDDING',
        'dealerIndex': 1,
        'biddingRound': 1,
        'floorCard': {'rank': '7', 'suit': '♦', 'value': 0},
        'players': [
            {'index': 0, 'hand': [
                {'rank': 'A', 'suit': '♥', 'value': 10},
                {'rank': 'K', 'suit': '♥', 'value': 4},
                {'rank': 'Q', 'suit': '♥', 'value': 3},
                {'rank': '7', 'suit': '♠', 'value': 0},
                {'rank': '8', 'suit': '♣', 'value': 0}
            ], 'position': 'Bottom'}
        ]
    }
    decision = bot.get_decision(game_state, 0)
    assert decision['action'] in ['SUN', 'ASHKAL'], f"Should bid SUN/ASHKAL with Sira help. Decision: {decision}"
    print("test_bid_with_sira PASSED")

def test_master_card_recognition():
    # Scenario: Bot has King Spades. Ace Spades is played. King should be Master.
    bot = bot_agent # Instance
    
    # Mock played cards via game_state
    # effectively Ace Spades played in previous trick
    game_state = {
        'phase': 'PLAYING',
        'gameMode': 'HOKUM',
        'trumpSuit': 'D', # Spades is non-trump
        'tableCards': [],
        'currentRoundTricks': [
            {'cards': [{'rank': 'A', 'suit': 'S', 'value': 0}, {'rank': '10', 'suit': 'S', 'value': 0}]}
        ],
        'players': [
            {'index': 0, 'hand': [
                {'rank': 'K', 'suit': 'S', 'value': 0}, # Should be Master now (in Hokum, K is under A)
                {'rank': '7', 'suit': 'H', 'value': 0}
            ], 'position': 'Bottom'}
        ]
    }
    
    decision = bot.get_decision(game_state, 0)
    # Expect leading King Spades (Index 0)
    assert decision['action'] == 'PLAY'
    assert decision['cardIndex'] == 0
    assert "Leading Master Card" in decision['reasoning']
    print("test_master_card_recognition PASSED")

def test_void_avoidance():
    # Scenario: Right opponent is void in Hearts (showed in history).
    # Bot (Bottom) has Hearts and Clubs. 
    # Bot should avoid leading Hearts (risk of cut).
    bot = bot_agent
    
    # Mock history: Trick 1 led Hearts, Right played Spades (Void in Hearts)
    trick1 = {
        'cards': [
            {'rank': 'A', 'suit': 'H', 'value': 0}, # Bottom led Hearts (hypothetically or partner)
            {'rank': '7', 'suit': 'S', 'value': 0}, # Right played Spades (RENEGE on Hearts)
            {'rank': '7', 'suit': 'H', 'value': 0}, 
            {'rank': '8', 'suit': 'H', 'value': 0}
        ],
        'playedBy': ['Top', 'Right', 'Left', 'Bottom'] # Who played what. 'Top' led. 'Right' cut/discarded.
    }
    
    game_state = {
        'phase': 'PLAYING',
        'gameMode': 'HOKUM',
        'trumpSuit': 'S', # Spades is Trump. Right has Spades (played one).
        'tableCards': [],
        'currentRoundTricks': [trick1],
        'players': [
            {'index': 0, 'hand': [
                {'rank': 'K', 'suit': 'H', 'value': 0}, # Risky Lead!
                {'rank': 'Q', 'suit': 'C', 'value': 0}  # Safe Lead
            ], 'position': 'Bottom'}
        ]
    }
    
    decision = bot.get_decision(game_state, 0)
    # Expect leading Clubs (Index 1) instead of Hearts
    assert decision['action'] == 'PLAY'
    assert decision['cardIndex'] == 1, f"Should avoid Hearts. Decision: {decision}" 
    # Reasoning might be 'Leading Weak Card' or similar for the SAFE card.
    # We just ensure it's NOT the risky card.
    print(f"Void Avoidance Decision Reasoning: {decision.get('reasoning')}")
    print("test_void_avoidance PASSED")

def test_endgame_all_masters():
    # Scenario: 3 Tricks left. Bot has A, 10, K of Spades (All Masters in SUN).
    # Bot should recognize "All Masters" and play to maximize points (Ace = 11).
    bot = bot_agent
    
    # Mock history: Assume all higher cards in other suits played or irrelevant.
    # We cheat by making played_cards contain nothing that beats A,10,K Spades.
    # In SUN, A > 10 > K.
    
    game_state = {
        'phase': 'PLAYING',
        'gameMode': 'SUN',
        'trumpSuit': None,
        'tableCards': [],
        'currentRoundTricks': [], # Empty history implies everything available, but we use is_master logic.
        # Ensure is_master returns True.
        # is_master checks if higher rank cards are unplayed.
        # If A is in hand, A is master.
        # If 10 is in hand, and A is in hand -> 10 is NOT master? 
        # Wait. is_master check: "Check all ranks HIGHER than mine... if test_card not in played_cards -> Return False"
        # If I have A and 10 in HAND.
        # A is master (No higher).
        # 10 is NOT master (A is unplayed).
        # So "All Masters" check will FAIL if I hold A and 10. 
        # Because 10 is blocked by A (which is in my hand, unplayed).
        
        # LOGIC FLAW FIX: is_master should consider "My Hand" as "Safe" or "Played"?
        # No, is_master means "Is this the Boss of the Table?".
        # If I hold A and 10. The 10 is NOT the boss. The A is.
        # So I can't say "All my cards are masters". Only the A is.
        # Once A is played, 10 becomes Master.
        
        # So the "All Masters" heuristic only works if I have a SEQUENCE of top cards?
        # NO. "All Masters" requires `is_master_card` to be true for ALL cards.
        # If I have A and K. K is not master.
        # So this heuristic only triggers if I have ONLY master cards. 
        # e.g. I have A Spades, A Hearts, A Clubs. (All separate suits).
        # OR if I have A Spades only.
    }
    
    # Let's test the "A Spades, A Hearts, A Clubs" scenario.
    game_state = {
        'phase': 'PLAYING',
        'gameMode': 'SUN', 
        'trumpSuit': None,
        'tableCards': [],
        'currentRoundTricks': [], 
        'players': [
            {'index': 0, 'hand': [
                {'rank': 'A', 'suit': 'S', 'value': 0}, 
                {'rank': 'A', 'suit': 'H', 'value': 0},
                {'rank': 'A', 'suit': 'C', 'value': 0}
            ], 'position': 'Bottom'}
        ]
    }
    
    decision = bot.get_decision(game_state, 0)
    assert decision['action'] == 'PLAY'
    # Should pick one of them.
    assert "Endgame Solver" in decision.get('reasoning', ''), f"Decision: {decision}"
    print("test_endgame_all_masters PASSED")


if __name__ == '__main__':
    print('Running tests...')
    tests = [obj for name, obj in globals().items() if name.startswith('test_') and callable(obj)]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f'PASS: {test.__name__}')
            passed += 1
        except AssertionError as e:
            print(f'FAIL: {test.__name__} - {e}')
            failed += 1
        except Exception as e:
            print(f'ERROR: {test.__name__} - {e}')
            traceback.print_exc()
            failed += 1
    
    print(f'Results: {passed} passed, {failed} failed')
    if failed > 0:
        sys.exit(1)

