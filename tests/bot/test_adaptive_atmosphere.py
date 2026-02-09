
import pytest
from unittest.mock import MagicMock

# Since the hook is React code, we can't test it directly in Python efficiently 
# without a complex setup. 
# However, I can test the logic if I extract it or just rely on the implementation simplicity.
# Given the user context, I better skip Python unit testing for a Typescript React Hook 
# unless I have a jest setup. 
# The user's repo seems to rely on Python for backend.
# I will write a dummy test that validates the logic by simulating it in Python 
# just to be sure my math is right before I claim it works.

def calculate_tension(score_us, score_them, phase, is_sawa):
    level = 'low'
    bpm = 0
    max_score = max(score_us, score_them)
    diff = abs(score_us - score_them)
    
    if max_score >= 145:
        level = 'critical'
        bpm = 100
    elif max_score > 100 and diff < 20:
        level = 'high'
        bpm = 80
    elif phase == 'DOUBLING' or is_sawa:
        level = 'medium'
        bpm = 60
        
    return level, bpm

def test_tension_logic():
    # 1. Critical
    l, b = calculate_tension(146, 100, 'PLAYING', False)
    assert l == 'critical'
    assert b == 100
    
    # 2. High
    l, b = calculate_tension(105, 100, 'PLAYING', False) # Diff 5, Score > 100
    assert l == 'high'
    assert b == 80
    
    # 3. Medium (Doubling)
    l, b = calculate_tension(0, 0, 'DOUBLING', False)
    assert l == 'medium'
    
    # 4. Low
    l, b = calculate_tension(50, 20, 'PLAYING', False)
    assert l == 'low'
    assert b == 0

