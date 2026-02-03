import pytest
from ai_worker.memory import CardMemory
from game_engine.models.card import Card

class TestSherlockMemory:
    @pytest.fixture
    def memory(self):
        return CardMemory()

    def test_void_tracking(self, memory):
        """Test that memory correctly infers voids from game events"""
        # Scenario: Player fails to follow suit
        # Led: Hearts, Player plays: Spades
        memory.mark_played("AH") # Ace Hearts Led
        memory.mark_void("Player1", "♥") # Player 1 couldn't follow hearts
        
        assert memory.is_void("Player1", "♥") == True
        assert memory.is_void("Player1", "♠") == False

    def test_contradiction_detection(self, memory):
        """Test Sherlock's ability to catch a liar"""
        # 1. Player 1 shows void in Hearts
        memory.mark_void("Player1", "♥")
        
        # 2. Player 1 tries to play Hearts (illegal if they have it, but here we test the detection of the lie)
        # Wait, if they show void, they shouldn't have it. 
        # But if they play it later, that proves the PREVIOUS void claim was a lie (or this play is illegal if they really are void).
        # In Baloot "Liar's Protocol":
        # Turn 1: Lead H. Player plays S (Claims Void H). Memory marks Void H.
        # Turn 2: Player plays H. Contradiction! 
        
        card = Card("♥", "K")
        contradiction = memory.check_contradiction("Player1", card)
        
        assert contradiction is not None
        assert "previously showed VOID" in contradiction

    def test_no_false_positive(self, memory):
        """Ensure honest plays don't trigger accusation"""
        memory.mark_void("Player1", "♥")
        
        # Player plays Spades (Consistent with void in Hearts)
        card = Card("♠", "K")
        contradiction = memory.check_contradiction("Player1", card)
        
        assert contradiction is None

    def test_reset_memory(self, memory):
        """Memory should clear between rounds"""
        memory.mark_void("Player1", "♥")
        memory.reset()
        assert memory.is_void("Player1", "♥") == False
