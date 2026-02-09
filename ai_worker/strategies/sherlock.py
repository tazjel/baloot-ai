import logging
import time
from typing import Dict, Any, Optional, Set, Tuple

# Use the centralized ForensicScanner logic
from ai_worker.strategies.components.forensics import ForensicScanner

logger = logging.getLogger(__name__)

class ForensicAdapter:
    """
    Adapts a raw game_state dictionary (from API/Socket) to the interface
    expected by ForensicScanner (which usually expects a Game object).
    """
    def __init__(self, game_state: Dict[str, Any]):
        self.game_state = game_state
        # CRITICAL: Use currentRoundTricks (completed tricks THIS round),
        # NOT roundHistory (past round RESULTS). The metadata with is_illegal
        # flags lives in currentRoundTricks after a trick resolves.
        self.round_history = game_state.get('currentRoundTricks', [])
        
        # Convert tableCards to match Game.table_cards structure if needed
        # Game.table_cards: [{'card': obj, 'playedBy': str, 'metadata': dict}]
        # API tableCards: [{'card': {suit, rank}, 'playedBy': str, 'metadata': dict}]
        self.table_cards = game_state.get('tableCards', [])
        
        # Mock State object for resolved_crimes
        class StateMock:
            def __init__(self, resolved):
                self.resolved_crimes = resolved or []
        
        self.state = StateMock(game_state.get('resolvedCrimes', []))


class SherlockStrategy:
    """
    The Detective Module (Refactored Phase 3).
    
    Responsibilities:
    1. Uses ForensicScanner to detect server-flagged crimes.
    2. Uses 'proof_hint' from metadata to construct valid accusations.
    3. Respects global ledger (resolvedCrimes) to prevent spam.
    """
    def __init__(self, agent):
        self.agent = agent
        self.reported_crimes: Set[Tuple] = set()
        self.pending_qayd_trigger = False
        self._last_round = -1  # Track current round to clear stale crimes
        self._last_crime = None  # Cache the last detected crime for accusation

    def scan_for_crimes(self, ctx, game_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Main entry point.
        """
        import datetime
        def _slog(msg):
            with open('logs/sherlock_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"{datetime.datetime.now().isoformat()} [SCAN] {msg}\n")
        
        # 0. Round Change Detection — Clear stale crime cache
        current_round = len(game_state.get('roundHistory', []))
        if current_round != self._last_round:
            _slog(f"Round changed {self._last_round} → {current_round}. Clearing {len(self.reported_crimes)} cached crimes.")
            self.reported_crimes.clear()
            self.pending_qayd_trigger = False
            self._last_crime = None
            self._last_round = current_round

        # 1. Check Global Locks
        qayd_state = game_state.get('qaydState', {})
        if qayd_state and qayd_state.get('active'):
            return self._handle_active_qayd(ctx, game_state, qayd_state)
            
        if self.pending_qayd_trigger:
            _slog(f"SKIP: pending_qayd_trigger=True")
            return None

        # 2. RUN FORENSIC SCANNER
        adapter = ForensicAdapter(game_state)
        scanner = ForensicScanner(adapter)
        
        # DON'T sync reported_crimes to scanner's _ignored_crimes — 
        # the scanner already deduplicates via is_illegal flag clearing and resolvedCrimes ledger.
        # Syncing reported_crimes caused NEW crimes (with is_illegal=True still set on live object)
        # to be silently skipped if they had the same trick_idx/card_idx as a previous detection.
        _slog(f"reported_crimes={self.reported_crimes}, pending={self.pending_qayd_trigger}")
        
        # Pre-scan debug: check table cards AND history directly
        tc = adapter.table_cards
        illegals = [i for i, c in enumerate(tc) if (c.get('metadata') or {}).get('is_illegal')]
        hist_illegals = []
        for ti, trick in enumerate(adapter.round_history):
            for ci, meta in enumerate(trick.get('metadata') or []):
                if meta and meta.get('is_illegal'):
                    hist_illegals.append((ti, ci))
        if illegals or hist_illegals:
            _slog(f"Pre-scan: {len(tc)} table cards, illegal at indices={illegals}, history_illegals={hist_illegals}")
        
        crime = scanner.scan()
        
        if crime:
            sig = (crime['trick_idx'], crime['card_idx'])  # 2-tuple matching ForensicScanner
            _slog(f"Crime found! sig={sig}, reported_crimes={self.reported_crimes}")
            if sig in self.reported_crimes:
                _slog(f"SKIP: sig already in reported_crimes")
                return None
            
            self.reported_crimes.add(sig)
            self.pending_qayd_trigger = True
            self._last_crime = crime
            
            logger.info(f"[SHERLOCK] 🕵️‍♂️ Detected Crime: {crime}")
            _slog(f"RETURNING QAYD_TRIGGER! crime={crime}")
            return {"action": "QAYD_TRIGGER"}
        else:
            if illegals:
                _slog(f"Scanner returned None despite illegals! resolved_crimes={game_state.get('resolvedCrimes', [])}")
                # Deep debug: check what scanner sees
                _slog(f"  adapter.round_history len={len(adapter.round_history)}")
                _slog(f"  adapter.table_cards count={len(adapter.table_cards)}")
                for i, tc_item in enumerate(adapter.table_cards):
                    meta = tc_item.get('metadata') or {}
                    _slog(f"  card[{i}] is_illegal={meta.get('is_illegal')} meta={meta}")

        return None

    def _handle_active_qayd(self, ctx, game_state, qayd_state) -> Dict[str, Any]:
        """
        Handle ongoing Qayd — build accusation from cached crime data.
        """
        self.pending_qayd_trigger = False 
        
        reporter_pos = qayd_state.get('reporter')
        
        # Am I the reporter?
        is_me = (reporter_pos == ctx.position)
        
        if is_me:
             # Use CACHED crime data (ForensicScanner clears is_illegal on scan,
             # so re-scanning will fail to find the crime)
             crime = self._last_crime
             
             if not crime:
                 # Fallback: Try re-scanning with a fresh scanner
                 logger.warning("[SHERLOCK] No cached crime! Trying fallback re-scan...")
                 adapter = ForensicAdapter(game_state)
                 scanner = ForensicScanner(adapter)
                 scanner._ignored_crimes = set()  # Force scan
                 crime = scanner.scan()
             
             if not crime:
                 logger.error("[SHERLOCK] Panic! Cannot find the crime I just triggered!")
                 return {"action": "QAYD_CANCEL"}
             
             # Extract Evidence
             crime_card = {
                 'suit': crime['suit'],
                 'rank': crime['rank'],
                 'trick_idx': crime['trick_idx'],
                 'card_idx': crime['card_idx'],
                 'played_by': crime['played_by']
             }
             
             # USE PROOF HINT
             proof_hint = crime.get('proof_hint')
             proof_card = None
             
             if proof_hint:
                 # Enrich proof with ownership info for RulesValidator
                 proof_card = dict(proof_hint)  # Copy to avoid mutating original
                 proof_card['played_by'] = crime['played_by']  # Same offender
                 proof_card['trick_idx'] = -1  # Card was in their hand
             else:
                 # Fallback (This shouldn't happen with new metadata logic)
                 logger.warning("[SHERLOCK] No proof_hint found! Using crime_card as fallback.")
                 proof_card = crime_card

             violation = crime.get('violation_type', 'REVOKE')

             logger.info(f"[SHERLOCK] Accusing {violation} with Proof: {proof_card}")
             
             return {
                 "action": "QAYD_ACCUSATION",
                 "accusation": {
                     "crime_card": crime_card,
                     "proof_card": proof_card,
                     "violation_type": violation
                 }
             }
             
        else:
             return {"action": "WAIT", "reason": "Qayd Investigation"}

    def detect_invalid_projects(self, game_state):
        # Placeholder for project logic
        return None


