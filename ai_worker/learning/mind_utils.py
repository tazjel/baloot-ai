
# Vocabulary Manager for MindReader

class MindVocab:
    PAD = 0
    START = 1
    
    # Offsets
    BID_OFFSET = 10
    PLAY_OFFSET = 50
    PLAYER_OFFSET = 100
    
    @staticmethod
    def get_card_token(card_str):
        # Card Format: 'S7', 'D10', 'HA', etc.
        # Suit: S=0, H=1, D=2, C=3
        # Rank: 7,8,9,10,Q,K,10,A -> 0..7
        # Total 32 cards.
        # Token = PLAY_OFFSET + Suit*8 + Rank
        if not card_str: return 0
        suits = {'S':0, 'H':1, 'D':2, 'C':3}
        ranks = {'7':0, '8':1, '9':2, '1':3, 'Q':4, 'K':5, '0':6, 'A':7} # '1' handles '10' usually if sliced 0
        # Handle '10' specifically 
        s = card_str[0]
        r = card_str[1:]
        if r == '10': r = '0' # use '0' key for 10
        
        if s not in suits or r not in ranks: return 0
        return MindVocab.PLAY_OFFSET + (suits[s] * 8) + ranks[r]

    @staticmethod
    def get_bid_token(bid_name):
        # SUN, HOKUM, PASS, etc.
        bids = {'PASS':0, 'SUN':1, 'HOKUM':2, 'ASHKAL':3}
        bn = bid_name.upper()
        if bn in bids:
            return MindVocab.BID_OFFSET + bids[bn]
        return 0
        
    @staticmethod
    def get_action_token(action_type, details):
        if action_type == 'BID':
            return MindVocab.get_bid_token(details)
        if action_type == 'PLAY':
            return MindVocab.get_card_token(details)
        return 0

    @staticmethod
    def card_to_index(card_str):
        # 0-31 index for output targets (NOT Tokens)
        # Same logic as token but 0-indexed
        return MindVocab.get_card_token(card_str) - MindVocab.PLAY_OFFSET
