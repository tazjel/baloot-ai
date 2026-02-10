from typing import List, Dict, Tuple, Any
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM, POINT_VALUES_SUN, POINT_VALUES_HOKUM
from game_engine.logic.referee import Referee
from server.logging_utils import logger, log_event

class TrickManager:
    def __init__(self, game):
        self.game = game
        # NOTE: qayd_state is managed exclusively by QaydEngine. Do NOT store it here.
        self.sawa_state = {"active": False, "claimer": None, "status": "NONE", "challenge_active": False}
        self.ignored_crimes = set() # Track cancelled accusations (trick_idx, card_idx)

    def get_card_points(self, card: Card) -> int:
        if self.game.game_mode == "SUN":
             return POINT_VALUES_SUN[card.rank]
        else:
             if card.suit == self.game.trump_suit:
                  return POINT_VALUES_HOKUM[card.rank]
             else:
                  return POINT_VALUES_SUN[card.rank]

    def get_trick_winner(self) -> int:
        lead_card = self.game.table_cards[0]['card']
        best_idx = 0
        current_best = -1
        
        for i, play in enumerate(self.game.table_cards):
            card = play['card']
            strength = -1
            
            if self.game.game_mode == "SUN":
                if card.suit == lead_card.suit:
                    strength = ORDER_SUN.index(card.rank)
            else:
                if card.suit == self.game.trump_suit:
                    strength = 100 + ORDER_HOKUM.index(card.rank)
                elif card.suit == lead_card.suit:
                    strength = ORDER_SUN.index(card.rank)
            
            if strength > current_best:
                current_best = strength
                best_idx = i
        return best_idx

    def can_beat_trump(self, winning_card: Card, hand: List[Card]) -> Tuple[bool, List[Card]]:
        winning_strength = 100 + ORDER_HOKUM.index(winning_card.rank)
        beating_cards = []
        for c in hand:
            if c.suit == self.game.trump_suit:
                 s = 100 + ORDER_HOKUM.index(c.rank)
                 if s > winning_strength:
                      beating_cards.append(c)
        return (len(beating_cards) > 0), beating_cards

    def is_valid_move(self, card: Card, hand: List[Card]) -> bool:
        try:
             from game_engine.logic.validation import is_move_legal
             
             # Prepare context
             # Map players to teams
             players_team_map = {p.position: p.team for p in self.game.players}
             my_idx = self.game.current_turn
             my_team = self.game.players[my_idx].team
             
             contract_variant = None
             bidding_engine = getattr(self.game, 'bidding_engine', None)
             if bidding_engine and hasattr(bidding_engine, 'contract') and bidding_engine.contract:
                 contract_variant = bidding_engine.contract.variant
             
             result = is_move_legal(
                 card=card,
                 hand=hand,
                 table_cards=self.game.table_cards,
                 game_mode=self.game.game_mode,
                 trump_suit=self.game.trump_suit,
                 my_team=my_team,
                 players_team_map=players_team_map,
                 contract_variant=contract_variant
             )
             if not result:
                  logger.error(f"❌ [TrickManager] ILLEGAL MOVE DETECTED: {card}")
             return result
        except Exception as e:
            logger.error(f"Error in is_valid_move: {e}")
            return True # Fallback

    def resolve_trick(self):
        winner_idx = self.get_trick_winner()
        winner_play = self.game.table_cards[winner_idx]
        winner_pos = winner_play['playedBy']
        
        winner_player = next(p for p in self.game.players if p.position == winner_pos)
        
        points = 0
        for play in self.game.table_cards:
             points += self.get_card_points(play['card'])
        
        # Update last trick for animation (include playedBy per card for DisputeModal)
        self.game.last_trick = {
            'cards': [{'card': tc['card'].to_dict(), 'playedBy': tc['playedBy']} for tc in self.game.table_cards], 
            'winner': winner_pos,
            'metadata': [tc.get('metadata') for tc in self.game.table_cards]
        }
        
        log_event("TRICK_WIN", self.game.room_id, details={
            "winner": winner_pos,
            "points": points,
            "trick_num": len(self.game.round_history) + 1
        })
        
        # Clear table
        trick_data = {
            "winner": winner_pos,
            "points": points,
            "cards": [{'card': t['card'].to_dict(), 'playedBy': t['playedBy']} for t in self.game.table_cards],
            "playedBy": [t['playedBy'] for t in self.game.table_cards],
            # Preserve metadata (including is_illegal) for Qayd checks
            "metadata": [t.get('metadata') for t in self.game.table_cards]
        }
        self.game.trick_history.append(trick_data)
        self.game.round_history.append(trick_data)
        
        self.game.table_cards = []
        self.game.current_turn = winner_player.index
        self.game.reset_timer() 
        
        # --- ANALYTICS: Track Win Probability ---
        prob = self.game.calculate_win_probability()
        self.game.win_probability_history.append({
            "trick": len(self.game.round_history),
            "us": prob
        }) 
        
        # --- PROJECT RESOLUTION (End of Trick 1) ---
        if len(self.game.round_history) == 1:
             # This will be handled by ProjectManager via Game delegation
             if hasattr(self.game, 'project_manager'):
                 self.game.project_manager.resolve_declarations()
             else:
                 # Fallback if refactor partial
                 if hasattr(self.game, 'resolve_declarations'):
                     self.game.resolve_declarations()

        # --- SAWA CHALLENGE CHECK ---
        if self.sawa_state.get('challenge_active', False):
             claimer_pos = self.sawa_state['claimer']
             claimer_team = 'us' if (claimer_pos in ['Bottom', 'Top']) else 'them'
             winner_team = 'us' if (winner_pos in ['Bottom', 'Top']) else 'them'
             
             if winner_team != claimer_team:
                  self.game.sawa_failed_khasara = True 
                  self.game.end_round()
                  return

        if not winner_player.hand:
            self.game.end_round()


    # --- SAWA LOGIC (Server-Validated, Fast Resolution) ---
    # Sawa = Grand Slam claim. Available only when hand ≤ 4 cards.
    # Server validates eligibility. No opponent "ACCEPT/REFUSE" flow.
    # Result is instant vs bots, 3-second timer vs humans only.

    def handle_sawa(self, player_index):
        """
        Player claims Sawa (guaranteed win of all remaining tricks).

        Flow:
          1. Gate: hand ≤ 4, it's their turn, table is empty
          2. Server runs check_sawa_eligibility()
          3a. Valid + all-bot opponents → instant resolve (round ends)
          3b. Valid + human opponents → 3s timer, then auto-resolve
          4a. Invalid + bot opponents → instant Qayd penalty
          4b. Invalid + human opponents → 3s timer for humans to call Qayd

        Returns dict with keys:
          success, sawa_resolved, sawa_penalty, sawa_pending_timer, sawa_valid
        """
        from game_engine.logic.rules.sawa import check_sawa_eligibility

        player = self.game.players[player_index]

        # --- BASIC GATES ---
        if player_index != self.game.current_turn:
            return {"success": False, "error": "Not your turn"}

        if not player.hand:
            return {"success": False, "error": "Hand empty"}

        if len(player.hand) > 4:
            return {"success": False, "error": "Sawa requires 4 or fewer cards remaining"}

        if len(self.game.table_cards) > 0:
            return {"success": False, "error": "Cannot call Sawa after playing a card"}

        # --- BUILD PLAYED CARDS SET ---
        played_cards = set()
        # From graveyard (most reliable)
        if hasattr(self.game, 'graveyard') and hasattr(self.game.graveyard, 'played_set'):
            played_cards = set(self.game.graveyard.played_set)
        else:
            # Fallback: from round history
            for trick in self.game.round_history:
                for c in trick.get('cards', []):
                    card_obj = c.get('card', c)
                    rank = card_obj.get('rank') if isinstance(card_obj, dict) else getattr(card_obj, 'rank', None)
                    suit = card_obj.get('suit') if isinstance(card_obj, dict) else getattr(card_obj, 'suit', None)
                    if rank and suit:
                        played_cards.add(f"{rank}{suit}")

        # --- SERVER-SIDE ELIGIBILITY CHECK ---
        is_valid = check_sawa_eligibility(
            hand=player.hand,
            played_cards=played_cards,
            trump_suit=self.game.trump_suit,
            game_mode=self.game.game_mode,
            phase=self.game.phase
        )

        claimer_pos = player.position
        claimer_team = 'us' if claimer_pos in ('Bottom', 'Top') else 'them'

        # Determine if any opponent is human
        opponents = [p for p in self.game.players if p.team != claimer_team]
        has_human_opponent = any(not p.is_bot for p in opponents)

        log_event("SAWA_CLAIM", getattr(self.game, 'room_id', None), details={
            "claimer": claimer_pos,
            "valid": is_valid,
            "cards_left": len(player.hand),
            "human_opponents": has_human_opponent
        })

        # Update sawa_state
        self.sawa_state.clear()
        self.sawa_state.update({
            "active": True,
            "claimer": claimer_pos,
            "claimer_index": player_index,
            "status": "PENDING",
            "valid": is_valid,
            "challenge_active": False,
            "cards_left": len(player.hand),
        })

        # --- RESOLUTION PATHS ---
        # If claimer is a bot, we trust the AI — auto-resolve instantly
        if player.is_bot:
            if is_valid:
                logger.info(f"[SAWA] VALID bot claim by {claimer_pos} — instant resolve (trusted AI)")
                self._resolve_sawa_win()
                return {"success": True, "sawa_resolved": True, "sawa_valid": True}
            else:
                # Bot made invalid Sawa (shouldn't happen but handle it)
                logger.warning(f"[SAWA] INVALID bot claim by {claimer_pos} — instant penalty")
                self._apply_sawa_penalty(claimer_pos, claimer_team)
                return {"success": True, "sawa_penalty": True, "sawa_valid": False}

        # Human claimer — use opponent-based resolution
        if is_valid:
            if not has_human_opponent:
                # All-bot opponents → instant resolve
                logger.info(f"[SAWA] VALID claim by {claimer_pos} — instant resolve (all bot opponents)")
                self._resolve_sawa_win()
                return {"success": True, "sawa_resolved": True, "sawa_valid": True}
            else:
                # Human opponents → 3s timer then auto-resolve
                logger.info(f"[SAWA] VALID claim by {claimer_pos} — 3s timer (human opponents)")
                self.sawa_state["status"] = "PENDING_TIMER"
                return {"success": True, "sawa_pending_timer": True, "sawa_valid": True, "timer_seconds": 3}
        else:
            if not has_human_opponent:
                # All-bot opponents → instant Qayd penalty
                logger.info(f"[SAWA] INVALID claim by {claimer_pos} — instant penalty (bots catch it)")
                self._apply_sawa_penalty(claimer_pos, claimer_team)
                return {"success": True, "sawa_penalty": True, "sawa_valid": False}
            else:
                # Human opponents → 3s timer for them to call Qayd
                logger.info(f"[SAWA] INVALID claim by {claimer_pos} — 3s timer (human opponents may catch)")
                self.sawa_state["status"] = "PENDING_TIMER"
                return {"success": True, "sawa_pending_timer": True, "sawa_valid": False, "timer_seconds": 3}

    def handle_sawa_timeout(self):
        """Called when the 3-second timer expires (human-vs-human games only)."""
        if not self.sawa_state.get('active') or self.sawa_state.get('status') != 'PENDING_TIMER':
            return {"success": False, "error": "No pending Sawa timer"}

        is_valid = self.sawa_state.get('valid', False)
        claimer_pos = self.sawa_state['claimer']

        if is_valid:
            # Valid claim, timer expired → resolve (humans didn't object)
            logger.info(f"[SAWA] Timer expired — valid claim by {claimer_pos}, resolving")
            self._resolve_sawa_win()
            return {"success": True, "sawa_resolved": True}
        else:
            # Invalid claim but no human called Qayd → lucky, resolve anyway
            logger.info(f"[SAWA] Timer expired — invalid claim by {claimer_pos} uncaught, resolving")
            self._resolve_sawa_win()
            return {"success": True, "sawa_resolved": True, "sawa_uncaught": True}

    def handle_sawa_qayd(self, reporter_index):
        """Human opponent calls Qayd on a Sawa claim during the 3s window."""
        if not self.sawa_state.get('active') or self.sawa_state.get('status') != 'PENDING_TIMER':
            return {"success": False, "error": "No pending Sawa to challenge"}

        reporter = self.game.players[reporter_index]
        claimer_pos = self.sawa_state['claimer']
        claimer_team = 'us' if claimer_pos in ('Bottom', 'Top') else 'them'
        reporter_team = 'us' if reporter.position in ('Bottom', 'Top') else 'them'

        # Only opponents can challenge
        if reporter_team == claimer_team:
            return {"success": False, "error": "Teammate cannot challenge Sawa"}

        is_valid = self.sawa_state.get('valid', False)

        if not is_valid:
            # Correct challenge! Apply penalty to the claimer
            logger.info(f"[SAWA] {reporter.position} caught invalid Sawa by {claimer_pos}!")
            self._apply_sawa_penalty(claimer_pos, claimer_team)
            return {"success": True, "sawa_penalty": True, "caught_by": reporter.position}
        else:
            # False challenge — the Sawa was actually valid
            # Penalize the challenger for false accusation
            logger.info(f"[SAWA] {reporter.position} falsely challenged valid Sawa by {claimer_pos}!")
            self._apply_sawa_penalty(reporter.position, reporter_team)
            return {"success": True, "sawa_penalty": True, "false_accusation": True,
                    "penalized": reporter.position}

    def _apply_sawa_penalty(self, loser_pos, loser_team):
        """Apply Qayd-style penalty for illegal Sawa claim."""
        winner_team = 'them' if loser_team == 'us' else 'us'

        log_event("SAWA_PENALTY", getattr(self.game, 'room_id', None), details={
            "loser": loser_pos, "loser_team": loser_team
        })

        self.sawa_state.update({
            "status": "PENALTY",
            "active": False,
            "penalty_team": loser_team,
        })

        # Use the existing Qayd penalty mechanism
        self.game.apply_qayd_penalty(loser_team, winner_team)

    def _resolve_sawa_win(self):
        """End round immediately, giving all remaining potential points to claimer's team."""
        claimer_pos = self.sawa_state["claimer"]

        log_event("SAWA_RESOLVED", getattr(self.game, 'room_id', None), details={
            "claimer": claimer_pos,
            "cards_collected": sum(len(p.hand) for p in self.game.players)
        })

        # Collect all cards from hands
        all_cards = []
        for p in self.game.players:
            all_cards.extend(p.hand)
            p.hand = []  # Empty hands

        # Create a dummy trick with all cards won by claimer
        total_trick_points = sum(self.get_card_points(c) for c in all_cards)

        dummy_trick = {
            'cards': [{'card': c.to_dict(), 'playedBy': claimer_pos} for c in all_cards],
            'winner': claimer_pos,
            'points': total_trick_points
        }

        self.game.round_history.append(dummy_trick)

        self.sawa_state.update({
            "status": "RESOLVED",
            "active": False,
        })

        self.game.end_round()

    def reset_state(self):
        self.sawa_state.clear()
        self.sawa_state.update({"active": False, "claimer": None, "status": "NONE", "challenge_active": False})

        # NOTE: qayd_state is managed exclusively by QaydEngine.
        # Do NOT touch it here. QaydEngine.reset() handles cleanup.

        self.ignored_crimes = set()
