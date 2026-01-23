
import sys
import os
import numpy as np
import rlcard
from rlcard.envs import Env

# Add parent directory to path to import game_logic
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_logic import Game, GamePhase, Card

class RLCardGameWrapper(Game):
    """Wrapper to make Game compatible with RLCard requirements"""
    def get_num_players(self):
        return 4
        
    def get_num_actions(self):
        return 32
        
    def get_player_id(self):
        return self.current_turn
        
    def is_over(self):
        return all(len(p.hand) == 0 for p in self.players)

    def get_state(self, player_id):
        return player_id


class BalootEnv(Env):
    def __init__(self, config=None):
        _config = {
            'allow_step_back': False,
            'seed': 42
        }
        if config:
            _config.update(config)
        config = _config

        self.game = None
        self.allow_step_back = False
        self.action_num = 32
        
        # Mappings
        self.SUITS = ['♠', '♥', '♦', '♣']
        self.RANKS = ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        
        self.card2id = {}
        self.id2card = {}
        
        idx = 0
        for s in self.SUITS:
            for r in self.RANKS:
                card_str = f"{r}{s}"
                self.card2id[card_str] = idx
                self.id2card[idx] = {'rank': r, 'suit': s}
                idx += 1
        
        # Initialize game before super().__init__ because RLCard expects it
        self.game = RLCardGameWrapper("training_room")
        self.game.allow_step_back = False # Patch for RLCard compatibility
        self.name = 'baloot'
        
        super().__init__(config)
        self.state_shape = [[102]] # RLCard often expects list of lists [[102]] for each player? Or just [102]? 
        # Check standard envs. Usually [shape].
        # Previous property returned [102].
        self.state_shape = [102] 

    def reset(self):

        """Reset the environment"""
        return self._init_game()

    def _init_game(self):
        """Initialize or reset the game"""
        self.game = RLCardGameWrapper("training_room")
        self.game.allow_step_back = False # Patch
        self.game.add_player("p0", "Player 0")
        self.game.add_player("p1", "Player 1")
        self.game.add_player("p2", "Player 2")
        self.game.add_player("p3", "Player 3")
        self.game.start_game()
        
        # Force bidding to finish for training purposes -> Simple logic:
        # For RL training on PLAYING phase, we might want to randomize bidding results 
        # or just force a standard contract.
        # Let's verify if the prompt implies full game or just playing.
        # "Play millions of games". A full game includes bidding.
        # BUT RLCard usually handles Steps.
        # game_logic starts in BIDDING. 
        # To simplify initial training, let's fast-forward bidding to a random contract
        # OR implement bidding actions.
        # The prompt implies "extract_state" has "Trump Suit" and "Mode", 
        # which implies we are in PLAYING phase.
        # I will implement a helper to fast-forward to Playing Phase with random contract.
        
        self._fast_forward_bidding()
        
        state, player_id = self.get_state_and_id()
        return state, player_id

    def _fast_forward_bidding(self):
        # Randomly choose a game mode and trump
        modes = ['SUN', 'HOKUM']
        mode = np.random.choice(modes)
        trump = None
        if mode == 'HOKUM':
            trump = np.random.choice(self.SUITS)
            
        # Manually set game state to PLAYING
        self.game.phase = GamePhase.PLAYING.value
        self.game.game_mode = mode
        self.game.trump_suit = trump
        self.game.bid = {"type": mode, "bidder": self.game.players[0].position, "doubled": False, "suit": trump}
        
        # Fix Card Distribution: Ensure everyone gets 8 cards.
        # Deck: 32. Initial: 20 (5x4). Floor: 1. Remaining: 11.
        # Bidder (P0) takes Floor (6). Needs 2 more.
        # Others (P1, P2, P3) need 3 more.
        # 2 + 3 + 3 + 3 = 11. Perfect match.
        
        if self.game.floor_card:
             self.game.players[0].hand.append(self.game.floor_card)
             self.game.floor_card = None

        for i, p in enumerate(self.game.players):
            if i == 0: # Bidder
                p.hand.extend(self.game.deck.deal(2))
            else:
                p.hand.extend(self.game.deck.deal(3))
            
        # Ensure current turn is correct for playing phase 
        # (Bidder leads? Or D+1? In Baloot, usually person on right of dealer? Or Bidder?)
        # Let's set turn to P0 (Bidder) for simplicity or D+1.
        self.game.current_turn = 0 # Bidder starts logic?
        
        # Handle valid moves for first player
        # e.g. if P0 plays


    def step(self, action, raw_action=False):
        """
        Action is an integer 0-31.
        """
        player_idx = self.game.current_turn
        player = self.game.players[player_idx]
        
        # Map integer action to card index in hand
        target_card_dict = self.id2card[action]
        rank = target_card_dict['rank']
        suit = target_card_dict['suit']
        
        # Find index in player's hand
        card_idx_in_hand = -1
        for i, c in enumerate(player.hand):
            if c.rank == rank and c.suit == suit:
                card_idx_in_hand = i
                break
                
        if card_idx_in_hand == -1:
            raise ValueError(f"Agent tried to play card {rank}{suit} but not in hand {player.hand}")

        # Execute Move
        res = self.game.play_card(player_idx, card_idx_in_hand)
        
        if "error" in res:
             raise ValueError(f"Engine rejected move: {res['error']}")
             
        # Check if game over (round finished)
        # All hands empty
        if all(len(p.hand) == 0 for p in self.game.players):
             return self.get_payoffs(), -1 # Return payoff and -1 id
        
        state, next_player_id = self.get_state_and_id()
        return state, next_player_id

    def is_over(self):
        # Game is over if all players have empty hands
        return all(len(p.hand) == 0 for p in self.game.players)

    def get_payoffs(self):
        # Return payoff for all players
        us_score = self.game.team_scores['us']

        them_score = self.game.team_scores['them']
        
        if us_score > them_score:
            return np.array([1.0, -1.0, 1.0, -1.0])
        elif them_score > us_score:
            return np.array([-1.0, 1.0, -1.0, 1.0])
        else:
            return np.array([0.0, 0.0, 0.0, 0.0])


    def get_legal_actions(self):
        player = self.game.players[self.game.current_turn]
        legal_indices = []
        for i, card in enumerate(player.hand):
            # Check validity using game engine
            if self.game.is_valid_move(card, player.hand):
                card_str = f"{card.rank}{card.suit}"
                legal_indices.append(self.card2id[card_str])
        
        # RLCard expects dict {action_id: None}
        return {idx: None for idx in sorted(legal_indices)}

    def _extract_state(self, player_id):
        player_idx = int(player_id) if isinstance(player_id, str) and player_id.startswith('p') else int(player_id)
        player = self.game.players[player_idx]
        
        # 1. Hand (32)
        obs_hand = np.zeros(32)
        for c in player.hand:
            idx = self.card2id[f"{c.rank}{c.suit}"]
            obs_hand[idx] = 1
            
        # 2. Public/Floor Card (32)
        obs_floor = np.zeros(32)
        if self.game.floor_card:
            fc = self.game.floor_card
            idx = self.card2id[f"{fc.rank}{fc.suit}"]
            obs_floor[idx] = 1
            
        # 3. Cards played in current trick (32)
        obs_trick = np.zeros(32)
        for tc in self.game.table_cards:
            c = tc['card']
            idx = self.card2id[f"{c.rank}{c.suit}"]
            obs_trick[idx] = 1
            
        # 4. Trump Suit (4)
        obs_trump = np.zeros(4)
        if self.game.trump_suit:
            suit_idx = self.SUITS.index(self.game.trump_suit)
            obs_trump[suit_idx] = 1
            
        # 5. Mode (2)
        obs_mode = np.zeros(2)
        if self.game.game_mode == 'SUN':
            obs_mode[0] = 1
        elif self.game.game_mode == 'HOKUM':
            obs_mode[1] = 1
            
        obs = np.concatenate([obs_hand, obs_floor, obs_trick, obs_trump, obs_mode])
        
        return {
            'obs': obs,
            'legal_actions': self.get_legal_actions(),
            'raw_obs': obs,
            'raw_legal_actions': self.get_legal_actions(),
            'action_record': [] # required by some agents
        }

    def get_state_and_id(self):
        # Helper required by rlcard
        player_id = self.game.current_turn
        state = self._extract_state(player_id)
        return state, player_id
        
    def get_player_id(self):
        return self.game.current_turn

