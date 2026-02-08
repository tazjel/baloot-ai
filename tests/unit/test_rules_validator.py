"""
Unit Tests for RulesValidator
==============================

Tests pure validation logic in isolation without mocking Game objects.

Run with: pytest tests/unit/test_rules_validator.py -v
"""

import pytest
from game_engine.logic.rules_validator import RulesValidator, ViolationType


class TestRevokeValidation:
    """Test REVOKE violation detection."""
    
    def test_valid_revoke_accusation(self):
        """
        Scenario: Player played Hearts when they had Spades (led suit).
        Proof: They played a Spade in a later trick.
        Expected: GUILTY
        """
        crime = {
            'suit': 'Hearts',
            'rank': 'Ace',
            'trick_idx': 0,
            'card_idx': 2,
            'played_by': 'Right'
        }
        
        proof = {
            'suit': 'Spades',  # Led suit
            'rank': 'King',
            'trick_idx': 1,  # Later trick
            'card_idx': 0,
            'played_by': 'Right'  # Same player
        }
        
        game_context = {
            'trump_suit': 'Clubs',
            'game_mode': 'HOKUM',
            'round_history': [
                {
                    'cards': [
                        {'card': {'suit': 'Spades', 'rank': 'Queen'}, 'playedBy': 'Bottom'},  # Led Spades
                        {'card': {'suit': 'Spades', 'rank': '10'}, 'playedBy': 'Right'},
                        {'card': {'suit': 'Hearts', 'rank': 'Ace'}, 'playedBy': 'Top'},  # CRIME
                    ],
                    'playedBy': ['Bottom', 'Right', 'Top'],
                    'metadata': [{}, {}, {}]
                },
                {
                    'cards': [
                        {'card': {'suit': 'Spades', 'rank': 'King'}, 'playedBy': 'Top'},  # PROOF
                    ],
                    'playedBy': ['Top'],
                    'metadata': [{}]
                }
            ],
            'table_cards': [],
            'players': []
        }
        
        is_guilty, reason = RulesValidator.validate(
            ViolationType.REVOKE,
            crime,
            proof,
            game_context
        )
        
        assert is_guilty is True
        assert 'قاطع' in reason or 'revoke' in reason.lower()
    
    def test_invalid_revoke_proof_wrong_suit(self):
        """
        Scenario: Proof card is not the led suit.
        Expected: NOT GUILTY
        """
        crime = {
            'suit': 'Hearts',
            'rank': 'Ace',
            'trick_idx': 0,
            'card_idx': 2,
            'played_by': 'Right'
        }
        
        proof = {
            'suit': 'Clubs',  # Wrong suit (not led suit)
            'rank': 'King',
            'trick_idx': 1,
            'card_idx': 0,
            'played_by': 'Right'
        }
        
        game_context = {
            'trump_suit': 'Clubs',
            'game_mode': 'HOKUM',
            'round_history': [
                {
                    'cards': [
                        {'card': {'suit': 'Spades', 'rank': 'Queen'}, 'playedBy': 'Bottom'},
                    ],
                    'playedBy': ['Bottom'],
                    'metadata': [{}]
                }
            ],
            'table_cards': [],
            'players': []
        }
        
        is_guilty, reason = RulesValidator.validate(
            ViolationType.REVOKE,
            crime,
            proof,
            game_context
        )
        
        assert is_guilty is False
        assert 'not the led suit' in reason.lower()
    
    def test_invalid_revoke_temporal_violation(self):
        """
        Scenario: Proof card was played BEFORE the crime.
        Expected: NOT GUILTY (can't prove they had it during crime)
        """
        crime = {
            'suit': 'Hearts',
            'rank': 'Ace',
            'trick_idx': 1,  # Later trick
            'card_idx': 0,
            'played_by': 'Right'
        }
        
        proof = {
            'suit': 'Spades',
            'rank': 'King',
            'trick_idx': 0,  # Earlier trick
            'card_idx': 0,
            'played_by': 'Right'
        }
        
        game_context = {
            'trump_suit': 'Clubs',
            'game_mode': 'HOKUM',
            'round_history': [
                {'cards': [{'card': {'suit': 'Spades', 'rank': 'King'}, 'playedBy': 'Right'}], 'playedBy': ['Right'], 'metadata': [{}]},
                {'cards': [{'card': {'suit': 'Hearts', 'rank': 'Ace'}, 'playedBy': 'Right'}], 'playedBy': ['Right'], 'metadata': [{}]},
            ],
            'table_cards': [],
            'players': []
        }
        
        is_guilty, reason = RulesValidator.validate(
            ViolationType.REVOKE,
            crime,
            proof,
            game_context
        )
        
        assert is_guilty is False
        assert 'before' in reason.lower()


class TestNoTrumpValidation:
    """Test NO_TRUMP violation detection."""
    
    def test_valid_no_trump_accusation(self):
        """
        Scenario: Player was void in led suit, had trump, but played non-trump.
        Proof: They played trump in a later trick.
        Expected: GUILTY
        """
        crime = {
            'suit': 'Hearts',  # Not trump
            'rank': 'Ace',
            'trick_idx': 0,
            'card_idx': 1,
            'played_by': 'Right'
        }
        
        proof = {
            'suit': 'Clubs',  # Trump
            'rank': 'Jack',
            'trick_idx': 1,
            'card_idx': 0,
            'played_by': 'Right'
        }
        
        game_context = {
            'trump_suit': 'Clubs',
            'game_mode': 'HOKUM',
            'round_history': [
                {'cards': [{'card': {'suit': 'Spades', 'rank': 'Queen'}, 'playedBy': 'Bottom'}], 'playedBy': ['Bottom'], 'metadata': [{}]},
            ],
            'table_cards': [],
            'players': []
        }
        
        is_guilty, reason = RulesValidator.validate(
            ViolationType.NO_TRUMP,
            crime,
            proof,
            game_context
        )
        
        assert is_guilty is True
        assert 'trump' in reason.lower() or 'دق' in reason
    
    def test_invalid_no_trump_sun_mode(self):
        """
        Scenario: NO_TRUMP violation in SUN mode (not applicable).
        Expected: NOT GUILTY
        """
        crime = {'suit': 'Hearts', 'rank': 'Ace', 'trick_idx': 0, 'card_idx': 0, 'played_by': 'Right'}
        proof = {'suit': 'Clubs', 'rank': 'Jack', 'trick_idx': 1, 'card_idx': 0, 'played_by': 'Right'}
        
        game_context = {
            'trump_suit': None,
            'game_mode': 'SUN',
            'round_history': [],
            'table_cards': [],
            'players': []
        }
        
        is_guilty, reason = RulesValidator.validate(
            ViolationType.NO_TRUMP,
            crime,
            proof,
            game_context
        )
        
        assert is_guilty is False
        assert 'hokum' in reason.lower()


class TestNoOvertrumpValidation:
    """Test NO_OVERTRUMP violation detection."""
    
    def test_valid_no_overtrump_accusation(self):
        """
        Scenario: Player played trump 10, but had trump Jack (higher).
        Expected: GUILTY
        """
        crime = {
            'suit': 'Clubs',  # Trump
            'rank': '10',
            'trick_idx': 0,
            'card_idx': 1,
            'played_by': 'Right'
        }
        
        proof = {
            'suit': 'Clubs',  # Trump
            'rank': 'Jack',  # Higher in HOKUM order
            'trick_idx': 1,
            'card_idx': 0,
            'played_by': 'Right'
        }
        
        game_context = {
            'trump_suit': 'Clubs',
            'game_mode': 'HOKUM',
            'round_history': [],
            'table_cards': [],
            'players': []
        }
        
        is_guilty, reason = RulesValidator.validate(
            ViolationType.NO_OVERTRUMP,
            crime,
            proof,
            game_context
        )
        
        assert is_guilty is True
        assert 'كبر' in reason or 'higher' in reason.lower()
    
    def test_invalid_no_overtrump_not_both_trump(self):
        """
        Scenario: Crime card is not trump.
        Expected: NOT GUILTY
        """
        crime = {'suit': 'Hearts', 'rank': '10', 'trick_idx': 0, 'card_idx': 0, 'played_by': 'Right'}
        proof = {'suit': 'Clubs', 'rank': 'Jack', 'trick_idx': 1, 'card_idx': 0, 'played_by': 'Right'}
        
        game_context = {
            'trump_suit': 'Clubs',
            'game_mode': 'HOKUM',
            'round_history': [],
            'table_cards': [],
            'players': []
        }
        
        is_guilty, reason = RulesValidator.validate(
            ViolationType.NO_OVERTRUMP,
            crime,
            proof,
            game_context
        )
        
        assert is_guilty is False
        assert 'both cards must be trump' in reason.lower()


class TestMetadataValidation:
    """Test metadata-based validation fallback."""
    
    def test_metadata_flagged_crime(self):
        """
        Scenario: Crime card has is_illegal=True flag in metadata.
        Expected: GUILTY
        """
        crime = {
            'suit': 'Hearts',
            'rank': 'Ace',
            'trick_idx': 0,
            'card_idx': 0,
            'played_by': 'Right'
        }
        
        game_context = {
            'trump_suit': 'Clubs',
            'game_mode': 'HOKUM',
            'round_history': [
                {
                    'cards': [{'card': {'suit': 'Hearts', 'rank': 'Ace'}, 'playedBy': 'Right'}],
                    'playedBy': ['Right'],
                    'metadata': [{'is_illegal': True, 'illegal_reason': 'Server detected revoke'}]
                }
            ],
            'table_cards': [],
            'players': []
        }
        
        is_guilty, reason = RulesValidator.validate(
            ViolationType.TRUMP_IN_DOUBLE,
            crime,
            None,
            game_context
        )
        
        assert is_guilty is True
        assert 'detected' in reason.lower()
    
    def test_metadata_not_flagged(self):
        """
        Scenario: Crime card has no is_illegal flag.
        Expected: NOT GUILTY
        """
        crime = {'suit': 'Hearts', 'rank': 'Ace', 'trick_idx': 0, 'card_idx': 0, 'played_by': 'Right'}
        
        game_context = {
            'trump_suit': 'Clubs',
            'game_mode': 'HOKUM',
            'round_history': [
                {
                    'cards': [{'card': {'suit': 'Hearts', 'rank': 'Ace'}, 'playedBy': 'Right'}],
                    'playedBy': ['Right'],
                    'metadata': [{}]
                }
            ],
            'table_cards': [],
            'players': []
        }
        
        is_guilty, reason = RulesValidator.validate(
            ViolationType.TRUMP_IN_DOUBLE,
            crime,
            None,
            game_context
        )
        
        assert is_guilty is False
        assert 'legal' in reason.lower()


# Run tests with: pytest tests/unit/test_rules_validator.py -v
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
