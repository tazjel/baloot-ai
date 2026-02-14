"""
game_engine/logic/baloot_manager.py — Baloot (K+Q of Trump) Declaration Manager
================================================================================

Handles the Baloot declaration in HOKUM mode.

Baloot = Holding both the King and Queen of the trump suit.

Rules (Official Baloot per pagat.com + competitive rules):
  1. Mode: HOKUM only (no trumps in SUN → no Baloot).
  2. Cards: Must hold both K and Q of the trump suit at deal time.
  3. Timing: Two-phase announcement:
     - Phase 1 "Baloot": Announced when the FIRST of the two cards is played.
     - Phase 2 "Re-baloot": Announced when the SECOND card is played.
     - Points are committed only after the Re-baloot (second card played).
  4. Scoring: Always worth 20 Abnat = 2 game points.
     - IMMUNE to doubling multipliers (always exactly 2 GP).
     - IMMUNE to project hierarchy (always scored, even if opponent has 100/400).
  5. Restriction: Cannot be scored if the player showed a 100-project
     containing K+Q, or showed 4-Kings or 4-Queens project.
  6. Either team can score Baloot, not just the contract buyer.
  7. Can coexist with Sira (3-seq) or 50 (4-seq) containing K+Q.
"""

from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BalootManager:
    """Manages Baloot (K+Q of trump) two-phase declaration tracking."""

    BALOOT_GAME_POINTS = 2   # Fixed: 20 Abnat ÷ 10 = 2 GP
    BALOOT_ABNAT = 20        # Raw point value

    def __init__(self, game):
        self.game = game
        # Track which players have played K or Q of trump
        # {position: set of ranks played ('K' and/or 'Q')}
        self._trump_royals_played: dict[str, set[str]] = {}
        # Track which players held both K+Q at deal time
        self._holders: set[str] = set()
        # Phase 1 announced: {position: True}
        self._phase1_announced: dict[str, bool] = {}
        # Phase 2 completed (scored): {position: True}
        self._declared: dict[str, bool] = {}

    def reset(self):
        """Reset state for a new round."""
        self._trump_royals_played.clear()
        self._holders.clear()
        self._phase1_announced.clear()
        self._declared.clear()

    def scan_initial_hands(self):
        """After dealing, scan who holds both K+Q of trump.

        Called after complete_deal() when hands are finalized.
        """
        trump = self.game.trump_suit
        if not trump or self.game.game_mode != 'HOKUM':
            return

        for p in self.game.players:
            ranks_in_trump = {c.rank for c in p.hand if c.suit == trump}
            if 'K' in ranks_in_trump and 'Q' in ranks_in_trump:
                self._holders.add(p.position)
                logger.debug(f"[BALOOT] {p.position} holds K+Q of trump {trump}")

    def on_card_played(self, position: str, card) -> Optional[dict]:
        """Called after a card is played. Tracks Baloot phases.

        Two-phase flow:
          - First K/Q of trump played → returns phase='BALOOT' (announcement)
          - Second K/Q of trump played → returns phase='RE_BALOOT' (scored)

        Args:
            position: The position of the player who played the card.
            card: The card object with .rank and .suit.

        Returns:
            dict with Baloot event info if triggered, else None.
        """
        trump = self.game.trump_suit
        if not trump or self.game.game_mode != 'HOKUM':
            return None

        # Only track K or Q of trump
        if card.suit != trump or card.rank not in ('K', 'Q'):
            return None

        # Only process for players who held both K+Q at deal
        if position not in self._holders:
            return None

        # Already fully declared — ignore
        if position in self._declared:
            return None

        # Check restriction before any announcement
        if self._is_blocked_by_project(position):
            logger.debug(f"[BALOOT] {position} blocked: 100-project or 4-K/4-Q contains K+Q")
            return None

        # Track this royal card
        if position not in self._trump_royals_played:
            self._trump_royals_played[position] = set()
        self._trump_royals_played[position].add(card.rank)

        played_count = len(self._trump_royals_played[position])
        team = self._get_team(position)

        if played_count == 1 and position not in self._phase1_announced:
            # ── Phase 1: "Baloot" — first card played ──
            self._phase1_announced[position] = True
            logger.info(f"[BALOOT] Phase 1: {position} announces Baloot ({card.rank}{card.suit})")
            return {
                'phase': 'BALOOT',
                'position': position,
                'team': team,
                'card_rank': card.rank,
                'card_suit': card.suit,
                'game_points': 0,  # Not scored yet
                'message': f'Baloot! {position} plays {card.rank} of trump {trump}',
            }

        elif played_count == 2 and position not in self._declared:
            # ── Phase 2: "Re-baloot" — second card played, points committed ──
            self._declared[position] = True
            logger.info(
                f"[BALOOT] Phase 2: {position} Re-baloot ({card.rank}{card.suit}) "
                f"— {self.BALOOT_GAME_POINTS} game points to team {team}"
            )
            return {
                'phase': 'RE_BALOOT',
                'declared': True,
                'position': position,
                'team': team,
                'card_rank': card.rank,
                'card_suit': card.suit,
                'game_points': self.BALOOT_GAME_POINTS,
                'abnat': self.BALOOT_ABNAT,
                'message': f'Re-baloot! {position} completes K+Q of trump {trump} — {self.BALOOT_GAME_POINTS} GP!',
            }

        return None

    def _is_blocked_by_project(self, position: str) -> bool:
        """Check if this player declared a 100-project containing K+Q of trump,
        or a 4-Kings or 4-Queens project (which blocks Baloot scoring).

        Sira (3-seq) and 50 (4-seq) do NOT block Baloot.
        """
        declarations = self.game.declarations
        if not declarations:
            return False

        player_decls = declarations.get(position, [])
        trump = self.game.trump_suit

        for decl in player_decls:
            dtype = decl.get('type', '')
            score = decl.get('score', 0)

            # 4-Kings or 4-Queens project always blocks Baloot
            if dtype in ('FOUR_OF_A_KIND', '100', 'HUNDRED'):
                rank = decl.get('rank')
                if rank in ('K', 'Q'):
                    return True

            # 100-project (5-in-sequence or 4-of-kind) containing K+Q blocks
            if score >= 100 and dtype in ('HUNDRED', '100', 'FOUR_OF_A_KIND'):
                cards = decl.get('cards', [])
                has_k = any(
                    (c.get('rank') == 'K' and c.get('suit') == trump) if isinstance(c, dict)
                    else (hasattr(c, 'rank') and c.rank == 'K' and c.suit == trump)
                    for c in cards
                )
                has_q = any(
                    (c.get('rank') == 'Q' and c.get('suit') == trump) if isinstance(c, dict)
                    else (hasattr(c, 'rank') and c.rank == 'Q' and c.suit == trump)
                    for c in cards
                )
                if has_k and has_q:
                    return True

        return False

    def _get_team(self, position: str) -> str:
        """Get the team of a player by position."""
        for p in self.game.players:
            if p.position == position:
                return p.team
        return 'us'  # fallback

    def get_baloot_points(self) -> dict[str, int]:
        """Get total Baloot game points per team for scoring.

        These points are ALWAYS 2 GP per declaration, NEVER multiplied
        by doubling level. They are added AFTER trick point conversion
        and doubling multiplication.

        Returns:
            {'us': int, 'them': int} with game points from Baloot declarations.
        """
        points = {'us': 0, 'them': 0}
        for position in self._declared:
            team = self._get_team(position)
            points[team] += self.BALOOT_GAME_POINTS
        return points

    def get_declarations(self) -> list[dict]:
        """Get list of Baloot declarations for round result."""
        result = []
        for position in self._declared:
            result.append({
                'type': 'BALOOT',
                'position': position,
                'team': self._get_team(position),
                'game_points': self.BALOOT_GAME_POINTS,
                'abnat': self.BALOOT_ABNAT,
            })
        return result

    def has_baloot(self, position: str) -> bool:
        """Check if a player currently holds K+Q of trump (for bot AI)."""
        return position in self._holders and position not in self._declared

    def get_state(self) -> dict:
        """Get serializable state for frontend."""
        return {
            'holders': list(self._holders),
            'phase1': list(self._phase1_announced.keys()),
            'declared': list(self._declared.keys()),
        }
