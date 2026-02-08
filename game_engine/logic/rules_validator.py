"""
RulesValidator — Pure Static Validation Logic for Qayd
======================================================

Extracted from QaydEngine to separate rule validation from state management.

Responsibilities:
- Validating Revoke accusations (failure to follow suit)
- Validating NO_TRUMP accusations (failure to trump when void)
- Validating NO_OVERTRUMP accusations (playing lower trump when holding higher)
- Validating TRUMP_IN_DOUBLE accusations (illegal trump in doubled games)
- Metadata-based validation fallback

Design Principle: Pure Functions
- All methods are static
- No side effects
- Deterministic (same input → same output)
- Easily testable in isolation
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

from game_engine.models.constants import ORDER_HOKUM, ORDER_SUN

logger = logging.getLogger(__name__)


class ViolationType:
    """Violation type constants (duplicated from qayd_engine for independence)."""
    REVOKE = 'REVOKE'
    TRUMP_IN_DOUBLE = 'TRUMP_IN_DOUBLE'
    NO_OVERTRUMP = 'NO_OVERTRUMP'
    NO_TRUMP = 'NO_TRUMP'


class RulesValidator:
    """
    Pure static validation logic for Qayd accusations.
    
    All methods are stateless and can be tested in isolation.
    """
    
    @staticmethod
    def validate(
        violation_type: str,
        crime: Dict[str, Any],
        proof: Optional[Dict[str, Any]],
        game_context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Main entry point for validation.
        
        Args:
            violation_type: ViolationType constant
            crime: Crime card data with {suit, rank, trick_idx, card_idx, played_by}
            proof: Proof card data (same structure), or None for metadata-only checks
            game_context: Game state context containing:
                - trump_suit: str
                - game_mode: str ('SUN' or 'HOKUM')
                - round_history: List[Dict]
                - table_cards: List[Dict]
                - players: List
        
        Returns:
            Tuple of (is_guilty: bool, reason: str)
        """
        if violation_type == ViolationType.REVOKE:
            if not proof:
                return False, "Revoke requires proof card"
            return RulesValidator._validate_revoke(crime, proof, game_context)
        
        elif violation_type == ViolationType.NO_TRUMP:
            if not proof:
                return False, "NO_TRUMP requires proof card"
            return RulesValidator._validate_no_trump(crime, proof, game_context)
        
        elif violation_type == ViolationType.NO_OVERTRUMP:
            if not proof:
                return False, "NO_OVERTRUMP requires proof card"
            return RulesValidator._validate_no_overtrump(crime, proof, game_context)
        
        elif violation_type == ViolationType.TRUMP_IN_DOUBLE:
            return RulesValidator._validate_via_metadata(crime, game_context)
        
        else:
            # Unknown violation type → fallback to metadata check
            return RulesValidator._validate_via_metadata(crime, game_context)
    
    # ══════════════════════════════════════════════════════════════════════════
    #  REVOKE VALIDATION
    # ══════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def _validate_revoke(
        crime: Dict[str, Any],
        proof: Dict[str, Any],
        ctx: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Revoke: Offender played wrong suit, proof shows they had the led suit.
        
        Logic:
        1. Find the led suit of the crime trick
        2. Verify crime card doesn't follow suit
        3. Verify proof card IS the led suit
        4. Verify proof was played by the same person
        5. Verify proof was played AFTER the crime (or still in hand)
        """
        offender_pos = crime.get('played_by')
        crime_trick_idx = crime.get('trick_idx', -1)
        proof_trick_idx = proof.get('trick_idx', -1)
        
        # Get crime trick
        crime_trick = RulesValidator._get_trick(crime_trick_idx, ctx)
        if not crime_trick:
            return False, "Crime trick not found in history"
        
        # Determine led suit
        led_suit = RulesValidator._get_led_suit(crime_trick)
        if not led_suit:
            return False, "Cannot determine led suit"
        
        # Check crime card
        crime_suit = crime.get('suit')
        if crime_suit == led_suit:
            return False, "Crime card follows suit — not a revoke"
        
        # Check proof card
        proof_suit = proof.get('suit')
        if proof_suit != led_suit:
            return False, f"Proof card ({proof_suit}) is not the led suit ({led_suit})"
        
        # Verify proof ownership
        proof_played_by = proof.get('played_by')
        if proof_played_by != offender_pos:
            return False, "Proof card was not played by the accused"
        
        # Temporal check: Proof must be from AFTER crime or still in hand
        # trick_idx == -1 means card is still in hand (future evidence)
        if proof_trick_idx >= 0 and proof_trick_idx <= crime_trick_idx:
            return False, "Proof card was played before or during the crime trick"
        
        return True, f"قاطع: {offender_pos} held {led_suit} but played {crime_suit}"
    
    # ══════════════════════════════════════════════════════════════════════════
    #  NO_TRUMP VALIDATION
    # ══════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def _validate_no_trump(
        crime: Dict[str, Any],
        proof: Dict[str, Any],
        ctx: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        NO_TRUMP: Offender didn't play trump when void in led suit and holding trump.
        
        Logic:
        1. Verify game mode is HOKUM
        2. Verify proof card IS trump
        3. Verify crime card is NOT trump
        4. Verify proof was played by accused
        5. Temporal check: Proof must be from after or in hand
        """
        game_mode = ctx.get('game_mode', '').upper()
        if 'HOKUM' not in game_mode:
            return False, "NO_TRUMP only applies to Hokum"
        
        trump_suit = ctx.get('trump_suit')
        if not trump_suit:
            return False, "Cannot determine trump suit"
        
        # Check proof card is trump
        proof_suit = proof.get('suit')
        if proof_suit != trump_suit:
            return False, f"Proof card ({proof_suit}) is not trump ({trump_suit})"
        
        # Check crime card is NOT trump
        crime_suit = crime.get('suit')
        if crime_suit == trump_suit:
            return False, "Crime card IS trump — they did trump"
        
        # Verify ownership
        offender_pos = crime.get('played_by')
        proof_played_by = proof.get('played_by')
        if proof_played_by != offender_pos:
            return False, "Proof card not played by accused"
        
        # Temporal check
        crime_trick_idx = crime.get('trick_idx', -1)
        proof_trick_idx = proof.get('trick_idx', -1)
        
        if proof_trick_idx >= 0 and proof_trick_idx <= crime_trick_idx:
            return False, "Proof card was played before or during crime"
        
        return True, f"ما دق بحكم: {offender_pos} had trump but didn't play it"
    
    # ══════════════════════════════════════════════════════════════════════════
    #  NO_OVERTRUMP VALIDATION
    # ══════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def _validate_no_overtrump(
        crime: Dict[str, Any],
        proof: Dict[str, Any],
        ctx: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        NO_OVERTRUMP: Offender played lower trump when holding higher trump.
        
        Logic:
        1. Verify game mode is HOKUM
        2. Verify both cards are trump
        3. Verify proof is STRONGER than crime
        4. Verify ownership
        """
        game_mode = ctx.get('game_mode', '').upper()
        if 'HOKUM' not in game_mode:
            return False, "NO_OVERTRUMP only applies to Hokum"
        
        trump_suit = ctx.get('trump_suit')
        if not trump_suit:
            return False, "Cannot determine trump suit"
        
        crime_suit = crime.get('suit')
        proof_suit = proof.get('suit')
        
        # Both must be trump
        if crime_suit != trump_suit or proof_suit != trump_suit:
            return False, "Both cards must be trump for overtrump violation"
        
        # Verify ownership
        offender_pos = crime.get('played_by')
        proof_played_by = proof.get('played_by')
        if proof_played_by != offender_pos:
            return False, "Proof card not played by accused"
        
        # Compare strengths using HOKUM order
        try:
            crime_rank = crime.get('rank')
            proof_rank = proof.get('rank')
            
            crime_strength = ORDER_HOKUM.index(crime_rank)
            proof_strength = ORDER_HOKUM.index(proof_rank)
            
            if proof_strength <= crime_strength:
                return False, "Proof card is not higher than crime card"
        
        except ValueError as e:
            logger.error(f"[RulesValidator] Invalid card rank: {e}")
            return False, "Invalid card rank"
        
        return True, f"ما كبر بحكم: {offender_pos} had higher trump but played lower"
    
    # ══════════════════════════════════════════════════════════════════════════
    #  METADATA VALIDATION (Fallback)
    # ══════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def _validate_via_metadata(
        crime: Dict[str, Any],
        ctx: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Fallback: Check if the card was flagged as illegal by the game engine.
        
        This relies on metadata.is_illegal flags set during gameplay.
        """
        trick_idx = crime.get('trick_idx', -1)
        card_idx = crime.get('card_idx', -1)
        
        # Check current table
        if trick_idx == len(ctx.get('round_history', [])):
            table_cards = ctx.get('table_cards', [])
            if 0 <= card_idx < len(table_cards):
                meta = table_cards[card_idx].get('metadata') or {}
                if meta.get('is_illegal'):
                    reason = meta.get('illegal_reason', 'Rule violation detected by engine')
                    return True, reason
        
        # Check round history
        round_history = ctx.get('round_history', [])
        if 0 <= trick_idx < len(round_history):
            trick = round_history[trick_idx]
            metas = trick.get('metadata') or []
            
            if 0 <= card_idx < len(metas) and metas[card_idx]:
                meta_entry = metas[card_idx]
                if isinstance(meta_entry, dict) and meta_entry.get('is_illegal'):
                    reason = meta_entry.get('illegal_reason', 'Rule violation detected')
                    return True, reason
        
        return False, "Move appears legal (no metadata flag found)"
    
    # ══════════════════════════════════════════════════════════════════════════
    #  HELPER UTILITIES
    # ══════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def _get_trick(trick_idx: int, ctx: Dict[str, Any]) -> Optional[Dict]:
        """
        Get trick data by index.
        
        Returns:
            Trick dict with {cards, playedBy, metadata} or None
        """
        round_history = ctx.get('round_history', [])
        table_cards = ctx.get('table_cards', [])
        
        # Current trick (in progress)
        if trick_idx == len(round_history):
            return {
                'cards': [{'card': c['card'], 'playedBy': c['playedBy']} for c in table_cards],
                'playedBy': [c['playedBy'] for c in table_cards],
                'metadata': [c.get('metadata', {}) for c in table_cards]
            }
        
        # Historical trick
        if 0 <= trick_idx < len(round_history):
            return round_history[trick_idx]
        
        return None
    
    @staticmethod
    def _get_led_suit(trick: Dict) -> Optional[str]:
        """
        Extract the led suit from a trick record.
        
        Handles multiple formats:
        - Flat dicts: {suit, rank}
        - Wrapped format: {card: {suit, rank}, playedBy: str}
        """
        cards = trick.get('cards', [])
        if not cards:
            return None
        
        first = cards[0]
        
        # Wrapped format
        if isinstance(first, dict) and 'card' in first:
            inner = first['card']
            if isinstance(inner, dict):
                return inner.get('suit')
            return getattr(inner, 'suit', None)
        
        # Flat format
        if isinstance(first, dict):
            return first.get('suit')
        
        # Object format
        return getattr(first, 'suit', None)
