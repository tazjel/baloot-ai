
import sys
import os
import json
import logging

# Setup Path
sys.path.append(os.getcwd())

from game_engine.models.card import Card
from ai_worker.bot_context import BotContext
from ai_worker.strategies.playing import PlayingStrategy
from ai_worker.strategies.bidding import BiddingStrategy
from game_engine.models.constants import BiddingPhase

# Configure separate logger to avoid noise
logging.basicConfig(level=logging.ERROR)

def parse_card_str(c_str):
    # Format: "J♠" or map rank/suit dict
    rank = c_str[:-1]
    suit = c_str[-1]
    return Card(suit, rank)

def create_context_from_case(case):
    setup = case['setup']
    mode = setup['mode'] # Can be None for bidding
    trump = setup['trump']
    my_hand_strs = setup['my_hand']
    my_hand = [parse_card_str(s) for s in my_hand_strs]
    
    table_strs = setup['table']
    table_cards = []
    for tc in table_strs:
         # format expected: {"rank": "A", "suit": "S", "playedBy": "Right"}
         c = Card(tc['suit'], tc['rank'])
         table_cards.append({'card': c.to_dict(), 'playedBy': tc['playedBy']})
         
    # History for memory
    history = setup.get('history', [])
    
    # Bidding Specifics
    phase_str = setup.get('phase', 'PLAYING')
    bidding_round = setup.get('bidding_round', 1)
    floor_dict = setup.get('floor_card')
    floor_card = None
    if floor_dict:
         floor_card = {'rank': floor_dict['rank'], 'suit': floor_dict['suit']}
    
    bidder = setup.get('bidder')
    bid_info = {}
    if mode: bid_info['type'] = mode
    if trump: bid_info['suit'] = trump
    if bidder: bid_info['bidder'] = bidder
    
    raw_state = {
        'players': [
            {'position': 'Bottom', 'team': 'us', 'hand': [c.to_dict() for c in my_hand], 'name': 'Bot'},
            {'position': 'Right', 'team': 'them', 'hand': [], 'name': 'Right'},
            {'position': 'Top', 'team': 'us', 'hand': [], 'name': 'Top'},
            {'position': 'Left', 'team': 'them', 'hand': [], 'name': 'Left'}
        ],
        'phase': phase_str,
        'biddingPhase': phase_str if phase_str == 'BIDDING' else None, # Simplified
        'gameMode': mode,
        'trumpSuit': trump,
        'tableCards': table_cards,
        'dealerIndex': 1,
        'bid': bid_info,
        'currentRoundTricks': history,
        'biddingRound': bidding_round,
        'floorCard': floor_card
    }
    
    return BotContext(raw_state, 0)

def run_benchmark():
    file_path = "tests/ai_iq/iq_test_cases.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)
        
    playing_strategy = PlayingStrategy()
    # Disable MCTS for IQ Benchmark (Heuristic Verification)
    if hasattr(playing_strategy, 'cognitive'):
        playing_strategy.cognitive.enabled = False
        
    bidding_strategy = BiddingStrategy()
    
    total = 0
    passed = 0
    results = []
    
    print(f"\n--- 🧠 BALOOT AI IQ TEST ---")
    print(f"Loaded {len(cases)} strategic scenarios.\n")
    
    for case in cases:
        total += 1
        ctx = create_context_from_case(case)
        category = case.get('category', 'PLAYING')
        
        # Decision
        try:
             decision = None
             if category == 'PLAYING':
                  decision = playing_strategy.get_decision(ctx)
             elif category == 'BIDDING':
                  decision = bidding_strategy.get_decision(ctx)
             
             # Evaluate
             expected_action = case.get('expected_action', 'PLAY')
             is_correct = False
             
             details = ""
             
             if category == 'PLAYING':
                  expected_card_str = case['expected_card']
                  expected_rank = expected_card_str[:-1]
                  expected_suit = expected_card_str[-1]
                  
                  chosen_idx = decision['cardIndex']
                  chosen_card = ctx.hand[chosen_idx]
                  
                  is_correct = (chosen_card.rank == expected_rank and chosen_card.suit == expected_suit)
                  details = f"Got: {chosen_card}"
                  if not is_correct: details += f" | Expected: {expected_card_str}"
                  
             elif category == 'BIDDING':
                  action = decision['action']
                  is_correct = (action == expected_action)
                  
                  if is_correct and action == 'HOKUM':
                       # Check suit
                       exp_suit = case.get('expected_suit')
                       got_suit = decision.get('suit')
                       if exp_suit and got_suit != exp_suit:
                            is_correct = False
                            details = f"Action Correct but Suit Wrong. Got: {got_suit} | Expected: {exp_suit}"
                  
                  if not details:
                       details = f"Action: {action}"
                       if not is_correct: details += f" | Expected: {expected_action}"

             # Keywords
             reason = decision.get('reasoning', '')
             keyword_match = True
             if 'reasoning_keyword' in case:
                  kw = case['reasoning_keyword']
                  if kw.lower() not in reason.lower():
                       keyword_match = False
                       
             status = "PASS" if is_correct else "FAIL"
             if is_correct and not keyword_match:
                  status = "WEAK PASS" # Right move, wrong reason?
             
             if is_correct: passed += 1
             
             print(f"[{status}] {case['id']}: {case['description']}")
             if status != "PASS":
                  print(f"   {details} ({reason})")
             else:
                  print(f"   Reasoning: {reason}")
                  
             results.append({'id': case['id'], 'status': status})
             
        except Exception as e:
             print(f"[ERROR] {case['id']}: {e}")
             import traceback
             traceback.print_exc()
             
    score = (passed / total) * 100
    print(f"\n--- RESULTS ---")
    print(f"Accuracy: {score:.1f}% ({passed}/{total})")
    
    iq_score = 100 + (passed * 10) # Arbitrary IQ mapping
    print(f"Estimated Bot IQ: {iq_score}")
    
    if score == 100:
         print("🌟 GENIUS LEVEL STRATEGY")
    elif score >= 75:
         print("✅ COMPETENT PLAYER")
    else:
         print("❌ NEEDS IMPROVEMENT")

if __name__ == "__main__":
    run_benchmark()
