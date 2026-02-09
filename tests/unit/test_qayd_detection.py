"""
Integration test for ForensicScanner detection pipeline.
Tests that the scanner correctly detects illegal moves in both
table_cards and round_history, and that dedup prevents re-detection.
"""
import pytest
from unittest.mock import MagicMock
from ai_worker.strategies.components.forensics import ForensicScanner


class MockGame:
    """Minimal game mock for ForensicScanner."""
    def __init__(self):
        self.table_cards = []
        self.round_history = []
        class StateMock:
            resolved_crimes = []
        self.state = StateMock()


class TestForensicScannerTableCards:
    """Bug 2: Scanner must detect illegal cards on table_cards."""

    def test_detects_illegal_card_on_table(self):
        game = MockGame()
        game.table_cards = [
            {'card': {'suit': 'HEARTS', 'rank': 'QUEEN'}, 'playedBy': 'Left', 'metadata': {}},
            {'card': {'suit': 'SPADES', 'rank': 'ACE'}, 'playedBy': 'Bottom', 'metadata': {
                'is_illegal': True,
                'illegal_reason': 'Revoke: had HEARTS but played SPADES',
                'proof_hint': {'suit': 'HEARTS', 'rank': 'ACE'}
            }},
        ]

        scanner = ForensicScanner(game)
        crime = scanner.scan()

        assert crime is not None, "Scanner should detect illegal card on table"
        assert crime['suit'] == 'SPADES'
        assert crime['rank'] == 'ACE'
        assert crime['played_by'] == 'Bottom'
        assert crime['trick_idx'] == 0  # no completed tricks yet
        assert crime['card_idx'] == 1
        assert crime['proof_hint'] == {'suit': 'HEARTS', 'rank': 'ACE'}

    def test_ignores_legal_cards(self):
        game = MockGame()
        game.table_cards = [
            {'card': {'suit': 'HEARTS', 'rank': 'QUEEN'}, 'playedBy': 'Left', 'metadata': {}},
            {'card': {'suit': 'HEARTS', 'rank': 'ACE'}, 'playedBy': 'Bottom', 'metadata': {}},
        ]

        scanner = ForensicScanner(game)
        crime = scanner.scan()

        assert crime is None, "No crime should be detected for legal cards"


class TestForensicScannerHistory:
    """Bug 2 (race condition): Scanner must detect illegal cards in round_history 
    when table_cards is already cleared by resolve_trick."""

    def test_detects_illegal_card_in_history(self):
        game = MockGame()
        game.table_cards = []  # Already cleared by resolve_trick!
        game.round_history = [{
            'winner': 'Left',
            'points': 10,
            'cards': [
                {'card': {'suit': 'HEARTS', 'rank': 'QUEEN'}, 'playedBy': 'Left'},
                {'card': {'suit': 'SPADES', 'rank': 'ACE'}, 'playedBy': 'Bottom'},
                {'card': {'suit': 'HEARTS', 'rank': '10'}, 'playedBy': 'Top'},
                {'card': {'suit': 'HEARTS', 'rank': 'KING'}, 'playedBy': 'Right'},
            ],
            'playedBy': ['Left', 'Bottom', 'Top', 'Right'],
            'metadata': [
                {},
                {'is_illegal': True, 'illegal_reason': 'Revoke: had HEARTS', 'proof_hint': {'suit': 'HEARTS', 'rank': 'ACE'}},
                {},
                {},
            ]
        }]

        scanner = ForensicScanner(game)
        crime = scanner.scan()

        assert crime is not None, "Scanner should detect illegal card in history"
        assert crime['suit'] == 'SPADES'
        assert crime['rank'] == 'ACE'
        assert crime['played_by'] == 'Bottom'
        assert crime['trick_idx'] == 0
        assert crime['card_idx'] == 1

    def test_history_detection_with_multiple_tricks(self):
        """Crime in trick 1 (2nd trick) should be found."""
        game = MockGame()
        game.table_cards = []
        game.round_history = [
            {  # Trick 0 — clean
                'cards': [{'card': {'suit': 'H', 'rank': 'Q'}, 'playedBy': 'L'}],
                'playedBy': ['L'], 'metadata': [{}]
            },
            {  # Trick 1 — has illegal card at index 2
                'cards': [
                    {'card': {'suit': 'H', 'rank': '10'}, 'playedBy': 'L'},
                    {'card': {'suit': 'H', 'rank': 'K'}, 'playedBy': 'B'},
                    {'card': {'suit': 'D', 'rank': 'J'}, 'playedBy': 'T'},
                    {'card': {'suit': 'H', 'rank': '9'}, 'playedBy': 'R'},
                ],
                'playedBy': ['L', 'B', 'T', 'R'],
                'metadata': [{}, {}, {'is_illegal': True, 'illegal_reason': 'Revoke'}, {}]
            },
        ]

        scanner = ForensicScanner(game)
        crime = scanner.scan()

        assert crime is not None
        assert crime['trick_idx'] == 1
        assert crime['card_idx'] == 2
        assert crime['played_by'] == 'T'


class TestDedupPreventsRedetection:
    """Bug 1: Dedup using 2-tuples must prevent re-detection."""

    def test_ignored_crimes_prevents_redetection(self):
        game = MockGame()
        game.table_cards = [
            {'card': {'suit': 'SPADES', 'rank': 'ACE'}, 'playedBy': 'Bottom', 'metadata': {
                'is_illegal': True, 'illegal_reason': 'Revoke'
            }},
        ]

        scanner = ForensicScanner(game)
        # Mark crime (trick_idx=0, card_idx=0) as already reported (2-tuple)
        scanner._ignored_crimes = {(0, 0)}

        crime = scanner.scan()
        assert crime is None, "Already-reported crime should be skipped"

    def test_ledger_prevents_redetection(self):
        game = MockGame()
        game.state.resolved_crimes = ["0_0"]  # Ledger entry
        game.table_cards = [
            {'card': {'suit': 'SPADES', 'rank': 'ACE'}, 'playedBy': 'Bottom', 'metadata': {
                'is_illegal': True, 'illegal_reason': 'Revoke'
            }},
        ]

        scanner = ForensicScanner(game)
        crime = scanner.scan()
        assert crime is None, "Ledger-resolved crime should be skipped"

    def test_new_crime_not_blocked_by_old_dedup(self):
        """Different crime signature should NOT be blocked."""
        game = MockGame()
        game.table_cards = [
            {'card': {'suit': 'H', 'rank': 'Q'}, 'playedBy': 'L', 'metadata': {}},
            {'card': {'suit': 'S', 'rank': 'A'}, 'playedBy': 'B', 'metadata': {
                'is_illegal': True, 'illegal_reason': 'Revoke'
            }},
        ]

        scanner = ForensicScanner(game)
        # Old crime was at (0, 0), new crime is at (0, 1)
        scanner._ignored_crimes = {(0, 0)}

        crime = scanner.scan()
        assert crime is not None, "New crime at different index should be detected"
        assert crime['card_idx'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
