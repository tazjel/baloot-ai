"""
ForensicScanner — AI-Powered Crime Detection Component
=======================================================

Extracted from QaydEngine._bot_auto_accuse to separate bot intelligence
from game rule enforcement.

Responsibilities:
- Scanning metadata flags (is_illegal) in table_cards and round_history
- Building accusation payloads for Qayd system
- Double Jeopardy prevention (session + ledger)
- Crime evidence packaging

Usage:
    scanner = ForensicScanner(game)
    crime = scanner.scan()
    if crime:
        bot_agent.trigger_qayd(crime)
"""

import logging
from typing import Optional, Dict, Any, Set, Tuple

logger = logging.getLogger(__name__)


class ForensicScanner:
    """
    Scans game state for illegal moves based on server-flagged metadata.
    
    This is the bot's "eyes" — it looks for crimes that the server has already
    validated and flagged, then packages the evidence for Qayd accusation.
    
    Design Principle: FIFO (First In, First Out)
    - Searches current trick first, then history in chronological order
    - Always reports the OLDEST unprosecuted crime
    """
    
    def __init__(self, game):
        """
        Args:
            game: Game instance with table_cards, round_history, state.resolved_crimes
        """
        self.game = game
        self._ignored_crimes: Set[Tuple[int, int]] = set()  # Session-based (in-memory)
    
    def scan(self) -> Optional[Dict[str, Any]]:
        """
        Main entry point. Scans for illegal moves in FIFO order.
        
        Returns:
            Dict with crime evidence if found:
            {
                'suit': str,
                'rank': str,
                'trick_idx': int,
                'card_idx': int,
                'played_by': str (PlayerPosition),
                'violation_type': str,
                'is_metadata_flagged': bool
            }
            
            None if no crime detected
        """
        # 1. Check Current Table (In-progress trick) — HIGHEST PRIORITY
        crime = self._scan_table_cards()
        if crime:
            return crime
        
        # 2. Check Completed Tricks (History) — FIFO Order
        crime = self._scan_history()
        if crime:
            return crime
        
        logger.debug("[ForensicScanner] No crimes detected")
        return None
    
    def _scan_table_cards(self) -> Optional[Dict[str, Any]]:
        """
        Scan current table_cards for is_illegal flags.
        
        Table structure:
        [
            {
                'card': {suit: str, rank: str},
                'playedBy': str,
                'metadata': {'is_illegal': bool, 'illegal_reason': str}
            },
            ...
        ]
        """
        trick_idx = len(self.game.round_history)  # Current trick is next index
        
        for card_idx, play in enumerate(self.game.table_cards):
            meta = play.get('metadata') or {}
            
            if not meta.get('is_illegal'):
                continue
            
            # Crime found — check if already reported
            sig = (trick_idx, card_idx)
            ledger_sig = f"{trick_idx}_{card_idx}"
            
            if self._is_already_reported(sig, ledger_sig):
                continue
            
            # Extract evidence
            card = play['card']
            played_by = play.get('playedBy')
            reason = meta.get('illegal_reason', 'Rule violation detected')
            
            crime_data = {
                'suit': card.suit if hasattr(card, 'suit') else card.get('suit'),
                'rank': card.rank if hasattr(card, 'rank') else card.get('rank'),
                'trick_idx': trick_idx,
                'card_idx': card_idx,
                'played_by': played_by,
                'violation_type': self._classify_violation(reason),
                'is_metadata_flagged': True,
                'reason': reason,
                'proof_hint': meta.get('proof_hint')
            }
            
            logger.info(
                f"[ForensicScanner] 🚨 Crime detected in current trick: "
                f"{played_by} played {crime_data['rank']} of {crime_data['suit']} "
                f"(Trick {trick_idx}, Card {card_idx})"
            )
            
            # Clear flag to prevent re-detection
            meta['is_illegal'] = False
            
            return crime_data
        
        return None
    
    def _scan_history(self) -> Optional[Dict[str, Any]]:
        """
        Scan completed tricks in FIFO order (oldest first).
        
        History structure:
        [
            {
                'cards': [
                    {'card': {suit, rank}, 'playedBy': str} OR {suit, rank}
                ],
                'playedBy': [str, str, str, str],
                'metadata': [{}, {}, {}, {}]
            },
            ...
        ]
        """
        if not self.game.round_history:
            return None
        
        # Scan in FORWARD order (FIFO)
        for trick_idx, trick in enumerate(self.game.round_history):
            metas = trick.get('metadata') or []
            cards = trick.get('cards', [])
            played_by_list = trick.get('playedBy', [])
            
            for card_idx, meta in enumerate(metas):
                if not meta or not meta.get('is_illegal'):
                    continue
                
                # Crime found — check reporting status
                sig = (trick_idx, card_idx)
                ledger_sig = f"{trick_idx}_{card_idx}"
                
                if self._is_already_reported(sig, ledger_sig):
                    continue
                
                # Extract card data (handle multiple formats)
                if card_idx >= len(cards):
                    logger.warning(f"[ForensicScanner] Metadata mismatch: card_idx {card_idx} >= len(cards) {len(cards)}")
                    continue
                
                c = cards[card_idx]
                card_inner = c.get('card', c) if isinstance(c, dict) else c
                
                # Determine played_by
                played_by = c.get('playedBy') if isinstance(c, dict) and 'playedBy' in c else (
                    played_by_list[card_idx] if card_idx < len(played_by_list) else None
                )
                
                if not played_by:
                    logger.warning(f"[ForensicScanner] Cannot determine played_by for trick {trick_idx}, card {card_idx}")
                    continue
                
                reason = meta.get('illegal_reason', 'Rule violation detected')
                
                crime_data = {
                    'suit': card_inner.get('suit') if isinstance(card_inner, dict) else getattr(card_inner, 'suit', None),
                    'rank': card_inner.get('rank') if isinstance(card_inner, dict) else getattr(card_inner, 'rank', None),
                    'trick_idx': trick_idx,
                    'card_idx': card_idx,
                    'played_by': played_by,
                    'violation_type': self._classify_violation(reason),
                    'is_metadata_flagged': True,
                    'reason': reason,
                    'proof_hint': meta.get('proof_hint')
                }
                
                logger.info(
                    f"[ForensicScanner] 🔍 Cold case found: "
                    f"{played_by} played {crime_data['rank']} of {crime_data['suit']} "
                    f"(Trick {trick_idx}, Card {card_idx})"
                )
                
                # Clear flag
                meta['is_illegal'] = False
                
                return crime_data
        
        return None
    
    def _is_already_reported(self, sig: Tuple[int, int], ledger_sig: str) -> bool:
        """
        Check if crime has been reported in session or ledger.
        
        Args:
            sig: (trick_idx, card_idx) tuple
            ledger_sig: "trick_idx_card_idx" string
        
        Returns:
            True if already reported (skip), False if new crime
        """
        # Session check (in-memory, cleared on round reset)
        if sig in self._ignored_crimes:
            logger.debug(f"[ForensicScanner] Crime {sig} already reported (session)")
            return True
        
        # Ledger check (persistent, survives round resets)
        if ledger_sig in self.game.state.resolved_crimes:
            logger.debug(f"[ForensicScanner] Crime {ledger_sig} already reported (ledger)")
            return True
        
        return False
    
    def _classify_violation(self, reason: str) -> str:
        """
        Classify violation type from reason string.
        
        Args:
            reason: Human-readable violation description
        
        Returns:
            ViolationType constant (REVOKE, NO_TRUMP, NO_OVERTRUMP, etc.)
        """
        reason_lower = reason.lower()
        
        if 'revoke' in reason_lower or 'قاطع' in reason_lower or 'follow suit' in reason_lower:
            return 'REVOKE'
        elif 'trump' in reason_lower and 'no trump' in reason_lower:
            return 'NO_TRUMP'
        elif 'overtrump' in reason_lower or 'كبر' in reason_lower:
            return 'NO_OVERTRUMP'
        elif 'double' in reason_lower or 'دبل' in reason_lower:
            return 'TRUMP_IN_DOUBLE'
        else:
            return 'REVOKE'  # Default fallback
    
    def mark_crime_ignored(self, trick_idx: int, card_idx: int):
        """
        Manually mark a crime as ignored (cancelled Qayd).
        
        This prevents re-reporting the same crime in the current session.
        The ledger system handles persistence across rounds.
        """
        sig = (trick_idx, card_idx)
        self._ignored_crimes.add(sig)
        logger.info(f"[ForensicScanner] Crime {sig} marked as ignored")
    
    def reset_session(self):
        """Clear session-based ignored crimes. Called on round reset."""
        self._ignored_crimes.clear()
        logger.debug("[ForensicScanner] Session crimes cleared")
    
    def get_stats(self) -> Dict[str, int]:
        """Get diagnostic statistics."""
        return {
            'session_ignored': len(self._ignored_crimes),
            'ledger_resolved': len(self.game.state.resolved_crimes) if hasattr(self.game.state, 'resolved_crimes') else 0,
        }
