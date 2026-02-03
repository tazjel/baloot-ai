import random
import time
import logging
import traceback
import copy
from functools import wraps
from typing import Dict, List, Optional, Any

from game_engine.models.constants import SUITS, RANKS, POINT_VALUES_SUN, POINT_VALUES_HOKUM, ORDER_SUN, ORDER_HOKUM, ORDER_PROJECTS, GamePhase, BiddingPhase, BidType
from game_engine.models.card import Card
from game_engine.models.deck import Deck
from game_engine.models.player import Player
from game_engine.logic.utils import sort_hand, scan_hand_for_projects, add_sequence_project, compare_projects, get_project_rank_order
from .timer_manager import TimerManager
from .phases.challenge_phase import ChallengePhase
from .project_manager import ProjectManager
from .scoring_engine import ScoringEngine
from .qayd_manager import QaydManager
from .trick_manager import TrickManager
from .phases.bidding_phase import BiddingPhase as BiddingLogic
from .phases.playing_phase import PlayingPhase as PlayingLogic

from .bidding_engine import BiddingEngine
from .forensic import ForensicReferee


# Configure Logging
from server.logging_utils import log_event, log_error, logger


def requires_unlocked(func):
    """
    Decorator to prevent execution when game is locked.
    Returns None if game is locked, otherwise executes the function.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.is_locked:
            logger.info(f"[LOCK] {func.__name__} skipped - game is locked")
            return None
        return func(self, *args, **kwargs)
    return wrapper

class Game:
    def __init__(self, room_id: str):
        self.room_id: str = room_id
        self.players = [] # List[Player]
        self.deck = Deck()
        self.table_cards = []  # List of {"playerId": id, "card": Card, "playedBy": position}
        self.current_turn = 0
        self.phase = GamePhase.WAITING.value
        self.dealer_index = 0
        self.bid = {"type": None, "bidder": None, "doubled": False}
        self.game_mode = None  # SUN or HOKUM
        self.trump_suit = None
        self.team_scores = {"us": 0, "them": 0}
        self.match_scores = {"us": 0, "them": 0}
        self.round_history = []  # List of tricks (Current Round)
        self.past_round_results = [] # HISTORY of RoundResult (Scores)
        self.trick_history = []  # Complete game tricks history for debug
        self.floor_card = None
        self.bidding_round = 1
        self.declarations = {} # Map[PlayerPosition] -> List[ProjectDict]
        self.trick_1_declarations = {} # Temp buffer for current round declarations
        self.is_project_revealing = False # State for animation
        self.initial_hands = {} # Snapshot of hands at start of round (for Replay)
        self.metadata = {} # For Time Lord/Ghost features (source_game_id, ghost_score, etc.)

        self.doubling_level = 1
        self.is_locked = False
        self.dealing_phase = 0  # 0=not started, 1=3 cards dealt, 2=5 cards dealt, 3=floor revealed
        self.last_trick = None  # Track last completed trick for animations 
        self.sawa_state = {"active": False, "claimer": None, "responses": {}, "status": "NONE", "challenge_active": False}
        self.sawa_failed_khasara = False # Flag if Sawa claim fails (Khasara triggered)
        self.akka_state = None # {claimer: pos, suits: [], timestamp: float}
        self.full_match_history = [] # Archives full round data: [{roundNum, tricks[], scores, bid...}]
        
        # Configuration
        self.strictMode = False # Default: False (Liar's Protocol Enabled)
        
        # Temporal Logic
        self.timer = TimerManager(5)
        self.timer_start_time = time.time() # Legacy / Read-only
        self.turn_duration = 30 # Legacy / Read-only
        self.timer_active = True # Legacy
        self.last_timer_reset = 0
        self.last_timer_reset = 0
        self.timer_paused = False # Flag for Professor or other pauses
        
        # Analytics
        self.win_probability_history = [] # List of {trick: int, us: float}
        self.blunders = {} # Map[PlayerPosition] -> count
        
        
        # Managers
        self.trick_manager = TrickManager(self)
        self.challenge_phase = ChallengePhase(self) # Refactored Handler
        self.project_manager = ProjectManager(self)
        self.scoring_engine = ScoringEngine(self)
        self.qayd_manager = QaydManager(self)

        # Initialize Phases Map
        self.phases = {
            GamePhase.BIDDING.value: BiddingLogic(self),
            GamePhase.PLAYING.value: PlayingLogic(self),
            GamePhase.CHALLENGE.value: self.challenge_phase,
        }

    @property
    def current_turn(self):
        """Returns the player whose turn it is, accounting for Gablak windows."""
        return self.bidding_engine.get_current_actor() if self.phase == GamePhase.BIDDING.value else self._current_turn
    
    @current_turn.setter
    def current_turn(self, value):
        self._current_turn = value

    def get_game_state(self) -> Dict[str, Any]:
        return {
            "roomId": self.room_id,
            "phase": self.phase,
            "biddingPhase": self.bidding_engine.phase.name if hasattr(self, 'bidding_engine') and self.bidding_engine else None,
            "players": [p.to_dict() for p in self.players],
            "players": [p.to_dict() for p in self.players],
            "tableCards": [{"playerId": tc['playerId'], "card": tc['card'].to_dict(), "playedBy": tc['playedBy'], "metadata": tc.get('metadata')} for tc in self.table_cards],
            "currentTurnIndex": self.current_turn, # Frontend expects currentTurnIndex
            "gameMode": self.game_mode,
            "trumpSuit": self.trump_suit,
            "bid": self.bid,
            "teamScores": self.team_scores,
            "matchScores": self.match_scores,
            "analytics": {
                "winProbability": self.win_probability_history,
                "blunders": self.blunders
            },
            "floorCard": self.floor_card.to_dict() if self.floor_card else None,
            "dealerIndex": self.dealer_index,
            "biddingRound": self.bidding_round,
            "declarations": { 
                pos: [ 
                    {**proj, 'cards': [c.to_dict() if hasattr(c, 'to_dict') else c for c in proj.get('cards', [])]} 
                    for proj in projs 
                ] 
                for pos, projs in self.declarations.items() 
            },
            "timer": {
                "remaining": self.timer.get_time_remaining(),
                "duration": self.timer.duration,
                "elapsed": self.timer.get_time_elapsed(),
                "active": self.timer.active
            },
            "isProjectRevealing": self.is_project_revealing,

            'doublingLevel': self.doubling_level,
            'isLocked': self.is_locked,
            'strictMode': self.strictMode,
            'dealingPhase': self.dealing_phase,
            'lastTrick': self.last_trick,
            'roundHistory': self.past_round_results,  # SCORING history (Required by Frontend)
        
            # Serialize currentRoundTricks fully
            # OPTIMIZED: Only send essential data for current round animation/state
            'currentRoundTricks': [
                {
                    'winner': t.get('winner'),
                    'points': t.get('points'),
                    # We might need cards for "Last Trick" view, but usually not entire history every tick
                    'cards': [
                        {**c, 'card': c['card'].to_dict()} if isinstance(c, dict) and 'card' in c and hasattr(c['card'], 'to_dict')
                        else (c.to_dict() if hasattr(c, 'to_dict') else c)
                        for c in t['cards']
                    ],
                    'playedBy': t.get('playedBy') # Expose who played the cards (needed for Bot Void detection)
                }
                for t in self.round_history
            ], 
            # 'trickHistory': self.trick_history,       # Full game debug - REMOVED for Optimization
            'sawaState': self.trick_manager.sawa_state if hasattr(self.trick_manager, 'sawa_state') else self.sawa_state,
            'qaydState': self.trick_manager.qayd_state if hasattr(self.trick_manager, 'qayd_state') else {},
            'challengeActive': (self.phase == GamePhase.CHALLENGE.value),
            
            # Timer Sync
            'timerStartTime': self.timer_start_time,
            'turnDuration': self.turn_duration,
            'serverTime': time.time(),
            
            'akkaState': self.project_manager.akka_state if hasattr(self.project_manager, 'akka_state') else self.akka_state,
            'gameId': self.room_id,
            'settings': getattr(self, 'settings', {}), # Expose Director Settings
            # OPTIMIZATION: Do not send full history on every tick. 
            # It should be fetched via a separate API call if needed.
            # 'fullMatchHistory': self.full_match_history 
        }

    def _sync_bid_state(self):
        """Syncs the Game.bid structure with current BiddingEngine state."""
        if not self.bidding_engine:
            return
            
        c = self.bidding_engine.contract
        tb = self.bidding_engine.tentative_bid
        
        # Priority 1: Current Finalized Contract
        if c.type:
            self.bid = {
                "type": c.type.value,
                "bidder": self.players[c.bidder_idx].position,
                "doubled": (c.level >= 2),
                "suit": c.suit,
                "level": c.level,
                "variant": c.variant,
                "isAshkal": c.is_ashkal,
                "isTentative": False
            }
        # Priority 2: Tentative Bid (during Gablak)
        elif tb:
            self.bid = {
                "type": tb['type'],
                "bidder": self.players[tb['bidder']].position,
                "doubled": False,
                "suit": tb['suit'],
                "level": 1,
                "variant": None,
                "isAshkal": (tb['type'] == 'ASHKAL'),
                "isTentative": True
            }
        else:
            self.bid = {"type": None, "bidder": None, "doubled": False}

    # --- AKKA LOGIC DELEGATION ---
    def check_akka_eligibility(self, player_index):
        return self.project_manager.check_akka_eligibility(player_index)

    # --- QAYD (FORENSIC) DELEGATION ---
    # NOTE: handle_qayd_trigger is defined in the HANDLERS section below (line ~1087)
    
    def handle_qayd_accusation(self, player_index, accusation=None):
        """
        Called when a bot provides specific accusation details.
        In the Forensic/Auto-Detect model, an accusation acts as a Confirmation of the found crime.
        """
        return self.qayd_manager.process_accusation(player_index, accusation) if accusation else self.handle_qayd_confirm()

    def handle_qayd_confirm(self):
        """Called when the user/bot confirms the verdict to apply penalty"""
        logger.info(f"[QAYD] Confirming Qayd verdict...")
        result = self.trick_manager.confirm_qayd()
        if result.get('success'):
             self.is_locked = False
             logger.info(f"[QAYD] Game UNLOCKED after confirmation. is_locked={self.is_locked}")
        return result
    
    
    def handle_qayd_cancel(self):
        """Called when Qayd is cancelled (False Alarm or User Cancel or Result Closed)"""
        result = self.qayd_manager.cancel_challenge()
        if result.get('success'):
             self.is_locked = False
             logger.info(f"[QAYD] Game UNLOCKED after cancel/close. is_locked={self.is_locked}")
        return result

    def handle_qayd(self, player_index, reason=None):
        """Legacy/Simple Qayd"""
        return self.handle_qayd_trigger(player_index)

    def handle_akka(self, player_index):
        return self.project_manager.handle_akka(player_index)

    # --- QAYD (FORENSIC) LOGIC ---
    # --- END QAYD DELEGATION ---


    @requires_unlocked
    def play_card(self, player_index: int, card_idx: int, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Delegates card play to PlayingPhase.
        """
        if self.phase != GamePhase.PLAYING.value:
            return {'success': False, 'error': f"Not in PLAYING phase. Current: {self.phase}"}

        # Check if PlayingPhase exists
        if GamePhase.PLAYING.value not in self.phases:
             self.phases = {
                GamePhase.BIDDING.value: BiddingPhase(self),
                GamePhase.PLAYING.value: PlayingPhase(self),
                GamePhase.CHALLENGE.value: self.challenge_phase,
             }
            
        return self.phases[GamePhase.PLAYING.value].play_card(player_index, card_idx, metadata)


    def add_player(self, id, name, avatar=None):
        # Check if player already exists
        for p in self.players:
            if p.id == id:
                p.name = name # Update name if changed
                if avatar: p.avatar = avatar # Update avatar if provided
                return p

        if len(self.players) >= 4:
            return None
        
        index = len(self.players)
        new_player = Player(id, name, index, self, avatar=avatar)
        self.players.append(new_player)
        return new_player

    def start_game(self) -> bool:
        if len(self.players) < 4:
            return False
        
        self.reset_round_state()
        
        # Set Random Dealer for the first game (Force Seed)
        self.dealer_index = random.randint(0, 3)
        logger.info(f"Game Started. Random Dealer Index: {self.dealer_index}")
        
        self.deal_initial_cards()
        self.phase = GamePhase.BIDDING.value
        
        # Initialize Bidding Engine
        self.bidding_engine = BiddingEngine(
             dealer_index=self.dealer_index, 
             floor_card=self.floor_card, 
             players=self.players,
             match_scores=self.match_scores
        )
        self.current_turn = self.bidding_engine.current_turn
        
        self.reset_timer() # Start timer for first bidder
        return True

    def reset_round_state(self):
        """Reset state for a new round while preserving match-level data"""
        self.deck = Deck()
        for p in self.players:
            p.hand = []
            p.captured_cards = []
            p.action_text = ''  # Clear action text
        
        self.table_cards = []
        self.bid = {"type": None, "bidder": None, "doubled": False}
        self.game_mode = None
        self.trump_suit = None
        self.floor_card = None
        self.bidding_round = 1
        self.declarations = {}
        self.trick_1_declarations = {}
        self.is_project_revealing = False
        self.initial_hands = {}

        self.round_history = []  # Trick history for this round
        self.is_locked = False
        self.doubling_level = 1
        self.dealing_phase = 0

        self.last_trick = None
        self.sawa_state = {"active": False, "claimer": None, "responses": {}, "status": "NONE", "challenge_active": False}
        self.sawa_failed_khasara = False
        self.sawa_state = {"active": False, "claimer": None, "responses": {}, "status": "NONE", "challenge_active": False}
        self.sawa_failed_khasara = False
        self.qayd_manager.reset()
        self.akka_state = None
        
        if hasattr(self, 'trick_manager'):
             self.trick_manager.sawa_state = self.sawa_state
             self.trick_manager.qayd_state = self.qayd_manager.state
        if hasattr(self.project_manager, 'akka_state'):
             self.project_manager.akka_state = None
             
        self.reset_timer()

        
    def deal_initial_cards(self):
        # Deal 5 to each
        for p in self.players:
            p.hand.extend(self.deck.deal(5))
        
        # Reveal Floor Card
        val = self.deck.deal(1)
        if val:
            self.floor_card = val[0]
            
    # --- PROJECT LOGIC ---
    def resolve_declarations(self):
        return self.project_manager.resolve_declarations() 


    @requires_unlocked
    def handle_bid(self, player_index: int, action: str, suit: Optional[str] = None, reasoning: Optional[str] = None) -> Dict[str, Any]:
        """
        Delegates bid handling to BiddingPhase.
        """
        if self.phase != GamePhase.BIDDING.value:
             return {'success': False, 'error': f"Not in BIDDING phase. Current: {self.phase}"}
             
        # Check if BiddingPhase exists
        if GamePhase.BIDDING.value not in self.phases:
             # Fallback if phases map logic fails or during reload
             self.phases = {
                GamePhase.BIDDING.value: BiddingPhase(self),
                GamePhase.PLAYING.value: PlayingPhase(self),
                GamePhase.CHALLENGE.value: self.challenge_phase,
             }
             
        return self.phases[GamePhase.BIDDING.value].handle_bid(player_index, action, suit, reasoning)

    def handle_double(self, player_index):
        try:
            if self.phase != GamePhase.BIDDING.value and self.phase != GamePhase.PLAYING.value:
                 pass
            
            # Check if bid exists
            if not self.bid['type']:
                 return {"error": "No bid to double"}
                 
            # Check eligibility (Opponent of bidder)
            bidder_pos = self.bid['bidder']
            doubler_pos = self.players[player_index].position
            
            is_same_team = (bidder_pos in ['Bottom', 'Top'] and doubler_pos in ['Bottom', 'Top']) or \
                           (bidder_pos in ['Right', 'Left'] and doubler_pos in ['Right', 'Left'])
                           
            if is_same_team:
                 return {"error": "Cannot double your partner"}
                 
            if self.doubling_level >= 2: # Limit to x2 for now, or x4 if Gahwa
                 return {"error": "Already doubled"}
                 
            self.doubling_level = 2
            self.bid['doubled'] = True
            self.is_locked = True # Locking prevents leading trump usually
            return {"success": True}
        except Exception as e:
             logger.error(f"Error in handle_double: {e}")
             return {"error": f"Internal Error: {str(e)}"}

    def complete_deal(self, bidder_index):
        # Give floor card to bidder
        bidder = self.players[bidder_index]
        if self.floor_card:
            bidder.hand.append(self.floor_card)
            self.floor_card = None
            
        # Deal remaining (2 to bidder, 3 to others)
        bidder.hand.extend(self.deck.deal(2))
        
        # Give 3 to everyone else
        for p in self.players:
            if p.index != bidder_index:
                p.hand.extend(self.deck.deal(3))
        
        # Sort Hands for all players
        for p in self.players:
             p.hand = sort_hand(p.hand, self.game_mode, self.trump_suit)
             p.action_text = "" # Clear "PASS" or other bidding texts
             # Capture Initial Hand for Replay
             self.initial_hands[p.position] = [c.to_dict() for c in p.hand]

        self.phase = GamePhase.PLAYING.value
        # Play starts from person RIGHT of dealer? Or Bidder?
        # Standard: Person to right of Dealer leads first.
        self.current_turn = (self.dealer_index + 1) % 4
        self.reset_timer()

    def handle_declare_project(self, player_index, type):
        return self.project_manager.handle_declare_project(player_index, type)

    # --- QAYD LOGIC DELEGATION ---
    def handle_qayd(self, reporter_index):
        return self.trick_manager.handle_qayd(reporter_index)

    def apply_khasara(self, loser_team, reason):
        return self.trick_manager.apply_khasara(loser_team, reason)

    # --- SAWA LOGIC DELEGATION ---
    def handle_sawa(self, player_index):
        result = self.trick_manager.handle_sawa(player_index)
        # Sync state for legacy access compatibility
        if hasattr(self.trick_manager, 'sawa_state'):
             self.sawa_state = self.trick_manager.sawa_state
        return result

    def _resolve_sawa_win(self):
        return self.trick_manager._resolve_sawa_win()

    def handle_sawa_response(self, player_index, response):
        result = self.trick_manager.handle_sawa_response(player_index, response)
        # Sync state
        if hasattr(self.trick_manager, 'sawa_state'):
             self.sawa_state = self.trick_manager.sawa_state
        return result

    def is_valid_move(self, card: Card, hand: List[Card]) -> bool:
        return self.trick_manager.is_valid_move(card, hand)

    def can_beat_trump(self, winning_card, hand):
        return self.trick_manager.can_beat_trump(winning_card, hand)

    def resolve_trick(self):
        return self.trick_manager.resolve_trick()



    
    # --- FORENSIC CHALLENGE ---
    def initiate_challenge(self, player_index):
        return self.qayd_manager.initiate_challenge(player_index)

    def process_accusation(self, player_index, accusation_data):
        return self.qayd_manager.process_accusation(player_index, accusation_data)



    def get_card_points(self, card):
        return self.trick_manager.get_card_points(card)

    def get_trick_winner(self):
        return self.trick_manager.get_trick_winner()




    def end_round(self, skip_scoring=False):
        log_event("ROUND_END", self.room_id, details={
            "scores": self.match_scores.copy(), 
            "round_history_length": len(self.round_history)
        })
        if not skip_scoring:
            # Delegate to Scoring Engine
            round_result, score_us, score_them = self.scoring_engine.calculate_final_scores()
            
            self.past_round_results.append(round_result)
            self.match_scores['us'] += score_us
            self.match_scores['them'] += score_them
            
            import copy
            serialized_declarations = {}
            for pos, projects in self.declarations.items():
                 serialized_declarations[pos] = []
                 for proj in projects:
                      new_proj = proj.copy()
                      if 'cards' in new_proj:
                           new_proj['cards'] = [c.to_dict() if hasattr(c, 'to_dict') else c for c in new_proj['cards']]
                      serialized_declarations[pos].append(new_proj)
                      
            round_snapshot = {
                'roundNumber': len(self.past_round_results),
                'bid': copy.deepcopy(self.bid),
                'scores': copy.deepcopy(round_result),
                'tricks': copy.deepcopy(self.round_history),
                'dealerIndex': self.dealer_index, 
                'floorCard': self.floor_card.to_dict() if self.floor_card else None,
                'declarations': serialized_declarations,
                'initialHands': self.initial_hands
            }
            self.full_match_history.append(round_snapshot)
            self.full_match_history.append(round_snapshot)
            try:
                 from ai_worker.agent import bot_agent
                 bot_agent.capture_round_data(round_snapshot)
            except Exception:
                 pass
        
        self.dealer_index = (self.dealer_index + 1) % 4
        # Check Win Condition
        if self.match_scores['us'] >= 152 or self.match_scores['them'] >= 152:
             log_event("GAME_END", self.room_id, details={"final_scores": self.match_scores.copy(), "winner": "us" if self.match_scores['us'] > self.match_scores['them'] else "them"})
             self.phase = GamePhase.GAMEOVER.value
             # Archive Match
             try:
                 from server.services.archiver import archive_match
                 archive_match(self)
             except Exception as e:
                 logger.error(f"Archive Trigger Failed: {e}")
        else:
             self.phase = GamePhase.FINISHED.value
             
        if hasattr(self, 'trick_manager'):
             self.trick_manager.reset_state()
             self.sawa_state = self.trick_manager.sawa_state
             self.qayd_state = self.trick_manager.qayd_state
        else:
             self.sawa_state = {"active": False, "claimer": None, "responses": {}, "status": "NONE", "challenge_active": False}
             self.qayd_state = {'active': False, 'reporter': None, 'reason': None, 'target_play': None}
             
        self.sawa_failed_khasara = False
        self.reset_timer()

    def calculate_win_probability(self):
        """
        Heuristic-based probability calculation.
        Formula: 50% + ((UsTotal - ThemTotal) / Target) * Weight
        """
        # 1. Calculate Current Round Points
        round_us = 0
        round_them = 0
        for trick in self.round_history:
            points = trick['points']
            winner_pos = trick['winner']
            if winner_pos in ['Bottom', 'Top']:
                round_us += points
            else:
                round_them += points
                
        # 2. Add Match Scores (Total Context)
        total_us = self.match_scores['us'] + round_us
        total_them = self.match_scores['them'] + round_them
        
        # 3. Apply Heuristic (Target 152)
        diff = total_us - total_them
        # Clamp diff to reasonable bounds (-152 to 152 effectively)
        prob = 0.5 + (diff / 152.0) * 0.5
        
        # Clamp result 0.0 to 1.0
        return max(0.0, min(1.0, prob))

    def increment_blunder(self, player_index):
        """Increments the blunder count for a specific player."""
        try:
            player = self.players[player_index]
            pos = player.position
            self.blunders[pos] = self.blunders.get(pos, 0) + 1
            logger.info(f"Blunder recorded for {pos}. Total: {self.blunders[pos]}")
        except Exception as e:
            logger.error(f"Error incrementing blunder: {e}")

    def reset_timer(self, duration=None):
        self.timer.reset(duration)
        self.timer_paused = False # Unpause on reset
        
        # Reset specific states
        self.qayd_state = {'active': False, 'reporter': None, 'reason': None, 'target_play': None}

    def pause_timer(self):
        """Pauses the turn timer (e.g. for Professor Intervention)"""
        self.timer_paused = True # Legacy flag for double safety
        self.timer.pause()
        logger.info(f"Timer Paused for Room {self.room_id}")

    def resume_timer(self):
        """Resumes the turn timer"""
        self.timer_paused = False
        self.timer.resume()
        logger.info(f"Timer Resumed for Room {self.room_id}")
        
    @requires_unlocked
    def check_timeout(self):
        """Called by background loop to check if current turn expired"""
        # Allow timeout check if Challenge is active (for Sherlock Bot)
        is_challenge = (self.phase == GamePhase.CHALLENGE.value) or (self.qayd_state.get('active'))
        
        if (not self.timer.active or self.timer_paused) and not is_challenge:
            return None
            
        # Don't check timeout in terminal phases
        if self.phase == GamePhase.FINISHED.value or self.phase == GamePhase.GAMEOVER.value:
            self.timer.stop()
            return None

        if self.timer.is_expired():
            lag = self.timer.get_lag()
            logger.info(f"[TIMEOUT] Timer expired. is_locked={self.is_locked}, phase={self.phase}")
            msg = f"Timeout Triggered for Player {self.current_turn} (Lag: {lag:.4f}s). Executing Action... | Room: {self.room_id} | GameObj: {id(self)}"
            logger.info(msg)
            with open("logs/timer_monitor.log", "a") as f:
                f.write(f"{time.time()} {msg}\n")
            
            t_start = time.time()
            res = None
            
            if self.phase == GamePhase.BIDDING.value:
                logger.info(f"Timeout Bidding for Player {self.current_turn}. Auto-PASS.")
                res = self.handle_bid(self.current_turn, "PASS")
            
            elif self.phase == GamePhase.DOUBLING.value:
                logger.info(f"Timeout Doubling for Player {self.current_turn}. Auto-PASS.")
                res = self.handle_bid(self.current_turn, "PASS")

            elif self.phase == GamePhase.VARIANT_SELECTION.value:
                 logger.info(f"Timeout Variant Selection for Player {self.current_turn}. Auto-OPEN.")
                 res = self.handle_bid(self.current_turn, "OPEN", "OPEN")
            
            elif self.phase == GamePhase.PLAYING.value:
                logger.info(f"Timeout Playing for Player {self.current_turn}. Auto-Play.")
                res = self.auto_play_card(self.current_turn)

            elif self.phase == GamePhase.CHALLENGE.value or self.qayd_state.get('active'):
                 # During Challenge/Qayd, if it's the Reporter's turn (conceptually), trigger them.
                 # Actually, current_turn might not be the reporter?
                 # We should trigger the reporter regardless of turn index in this special state?
                 # Or rely on reporter index being passed.
                 reporter_pos = self.qayd_state.get('reporter')
                 reporter_idx = next((p.index for p in self.players if p.position == reporter_pos), -1)
                 
                 if reporter_idx != -1:
                      logger.info(f"Timeout/Action Cycle for Qayd Reporter {reporter_pos} ({reporter_idx}).")
                      res = self.auto_play_card(reporter_idx)
                 else:
                      logger.warning("Qayd Active but reporter not found.")
            
            dur = time.time() - t_start
            logger.info(f"Timeout Action Completed in {dur:.4f}s. Result: {res}")
             
            # Fallback: If action was successful but timer wasn't reset (bug in phase handler), do it here.
            # Also ensures socket_handler saves the game.
            if res and res.get('success'):
                 if self.timer.is_expired():
                      logger.warning("Action successful but timer still expired. Forcing reset.")
                      self.reset_timer()

            return res
                
        return None

    def handle_qayd(self, player_index, reason):
        try:
            reporter = self.players[player_index]
            self.timer_active = False 
            
            logger.info(f"QAYD raised by {reporter.name} ({reporter.position}) for {reason}")
            
            self.qayd_state = {
                'active': True, 
                'reporter': reporter.position, 
                'reason': reason,
                'target_play': self.last_trick 
            }
            
            is_valid_claim = False
            
            if reason == "FALSE_SAWA":
                 if self.sawa_failed_khasara: is_valid_claim = True
            
            if is_valid_claim:
                 offender_team = 'them' if reporter.team == 'us' else 'us'
                 self.apply_qayd_penalty(offender_team, reporter.team)
                 return {"success": True, "result": "VALID", "message": "Qayd Upheld - Penalty Applied"}
            else:
                 self.apply_qayd_penalty(reporter.team, 'them' if reporter.team == 'us' else 'us')
                 return {"success": True, "result": "INVALID", "message": "False Alarm - Reporter Penalized"}
                 
        except Exception as e:
            logger.error(f"Error in handle_qayd: {e}")
            return {"error": str(e)}

    def apply_qayd_penalty(self, loser_team, winner_team):
        max_points = 26 if self.game_mode == 'SUN' else 16
        
        score_loser = 0
        score_winner = max_points 
        
        self.match_scores[winner_team] += score_winner
        self.match_scores[loser_team] += score_loser 
        
        round_result = {
            'roundNumber': len(self.past_round_results) + 1,
            'us': {'gamePoints': score_winner if winner_team == 'us' else 0, 'isKaboot': True},
            'them': {'gamePoints': score_winner if winner_team == 'them' else 0, 'isKaboot': True},
            'winner': winner_team,
            'qayd': True
        }
        self.past_round_results.append(round_result)
        
        # Archiving for Replay
        # Qayd ends the round abruptly, but we should still record it.
        # However, we don't have tricks.
        # We'll snapshot with empty tricks or whatever occurred.
        # Logic similar to end_round but simpler.
        round_snapshot = {
                'roundNumber': len(self.past_round_results),
                'bid': copy.deepcopy(self.bid),
                'scores': copy.deepcopy(round_result),
                'tricks': [], # No tricks played usually if Qayd happens early? Or insert self.round_history?
                'dealerIndex': self.dealer_index, 
                'floorCard': self.floor_card.to_dict() if self.floor_card else None,
                'declarations': {}, # Usually checking cards triggers Qayd, declarations might not exist
                'initialHands': self.initial_hands
        }
        # If Qayd happened during a trick, maybe we should save round_history?
        # For now, empty tricks is safer than broken state.
        self.full_match_history.append(round_snapshot)
        
        self.dealer_index = (self.dealer_index + 1) % 4
        
        if self.match_scores['us'] >= 152 or self.match_scores['them'] >= 152:
             log_event("GAME_END", self.room_id, details={"final_scores": self.match_scores.copy(), "winner": "us" if self.match_scores['us'] > self.match_scores['them'] else "them"})
             self.phase = GamePhase.GAMEOVER.value
        else:
             self.phase = GamePhase.FINISHED.value
             
        self.qayd_state = {'active': False, 'reporter': None, 'reason': None, 'target_play': None}

    @requires_unlocked
    def auto_play_card(self, player_index):
        try:
            player = self.players[player_index]
            if not player.hand:
                return {"error": "Hand empty"}
                
            t0 = time.time()
            from ai_worker.agent import bot_agent
            decision = bot_agent.get_decision(self.get_game_state(), player_index)
            dt = time.time() - t0
            logger.info(f"Auto-Play Decision Latency for {player.name}: {dt:.4f}s")
            
            card_idx = decision.get('cardIndex', 0)
            action = decision.get('action', 'PLAY_CARD')
            
            if action == 'QAYD_TRIGGER':
                 logger.info(f"Auto-Play for {player.name}: Triggering Qayd Protocol (Sherlock)")
                 return self.handle_qayd_trigger(player_index)
                 
            elif action == 'QAYD_ACCUSATION':
                 logger.info(f"Auto-Play for {player.name}: Submitting Qayd Accusation")
                 # Ensure we have payload
                 payload = decision.get('accusation', {})
                 
                 # FIX: Check Phase to route correctly
                 if self.phase == GamePhase.CHALLENGE.value:
                      return self.process_accusation(player_index, payload)
                 else:
                      # If not in Challenge Phase yet, treat Accusation as a Trigger first
                      logger.info(f"Auto-Play: QAYD_ACCUSATION received in {self.phase}. Triggering Investigation first.")
                      return self.handle_qayd_trigger(player_index)

            elif action == 'WAIT':
                 reason = decision.get('reason', 'Waiting')
                 if reason != "Qayd Investigation in Progress":
                      logger.info(f"Auto-Play for {player.name}: WAIT ({reason})")
                 return {"success": True, "action": "WAIT", "message": reason}

            if card_idx < 0 or card_idx >= len(player.hand):
                card_idx = 0 
                
            if not self.is_valid_move(player.hand[card_idx], player.hand):
                 for i, c in enumerate(player.hand):
                      if self.is_valid_move(c, player.hand):
                           card_idx = i
                           break

            logger.info(f"Auto-Play for {player.name}: Bot chose index {card_idx}")
            return self.play_card(player_index, card_idx)
            
        except Exception as e:
            logger.error(f"Error in auto_play_card: {e}")
            # Fallback: Play ANY valid card
            player = self.players[player_index]
            for i, c in enumerate(player.hand):
                 if self.is_valid_move(c, player.hand):
                      logger.info(f"Auto-Play Fallback for {player.name}: Playing index {i} ({c.rank}{c.suit})")
                      return self.play_card(player_index, i)
            
            return {"error": f"Auto-Play Failed completely: {e}"}

    # --- HANDLERS (Restored / New) ---
    def handle_akka(self, player_index):
        """Delegate Akka to ProjectManager"""
        if hasattr(self, 'project_manager'):
             return self.project_manager.handle_akka(player_index)
        return {'success': False, 'error': 'ProjectManager missing'}

    def handle_qayd_trigger(self, player_index):
        # DELEGATED to ChallengePhase (Refactor Step 1)
        return self.challenge_phase.trigger_investigation(player_index)
        


    def handle_qayd_accusation(self, player_index, accusation=None):
        """Alias for trigger"""
        return self.handle_qayd_trigger(player_index)

    def handle_qayd_confirm(self):
        """Called to confirm verdict"""
        # DELEGATED to ChallengePhase (Refactor Step 1)
        return self.challenge_phase.resolve_verdict()

    # --- PICKLE SUPPORT ---
    def __getstate__(self):
        """Custom pickle state to exclude non-pickleable or transient objects."""
        state = self.__dict__.copy()
        # TimerManager might be fine, but if it has locks (future), let's be safe.
        # Actually timer is just floats.
        # But let's check if there are any other issues.
        # If we have threading.Lock or socket objects, remove them.
        # For now, we assume simple state.
        # However, to be extra safe against 'can't pickle local object' from closures:
        
        # We need to ensure we don't pickle anything that might fail.
        # If 'room_manager' was attached, we'd remove it.
        # 'logger' objects are not pickleable.
        if 'logger' in state: del state['logger']
        
        return state

    def __setstate__(self, state):
        """Restore state and re-initialize transient objects."""
        self.__dict__.update(state)
        # Re-init logger if needed, though usually it's global
        # Ensure timer is active if it was
        if not hasattr(self, 'timer'):
             self.timer = TimerManager(5)
