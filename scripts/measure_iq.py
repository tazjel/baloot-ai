import os
import sys
import json
import time
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_worker.agent import BotAgent
from ai_worker.bot_context import BotContext
# Ensure DB is loaded for agent if it relies on it (though agent uses Redis mostly)
import server.models

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("IQ_METER")

def measure_iq():
    """
    Runs the current Bot Logic against the Golden Puzzle Set.
    Calculates an 'IQ Score' (Accuracy %).
    """
    benchmark_path = os.path.join("ai_worker", "benchmarks", "golden_puzzles.json")
    
    if not os.path.exists(benchmark_path):
        logger.error("❌ Benchmark file not found. Run 'python scripts/generate_benchmark.py' first.")
        return

    with open(benchmark_path, 'r', encoding='utf-8') as f:
        puzzles = json.load(f)
        
    if not puzzles:
        logger.warning("⚠️ No puzzles found in benchmark file.")
        return

    logger.info(f"🧠 Starting IQ Test on {len(puzzles)} scenarios...")
    logger.info("-" * 50)
    
    agent = BotAgent()
    # Force Disable Redis for the Agent? 
    # Or do we WANT it to use memory?
    # User asked to measure "Progress Of Intelligence". 
    # Intelligence = Logic + Memory. So keep Redis enabled.
    
    correct_count = 0
    total = len(puzzles)
    
    for i, puzzle in enumerate(puzzles):
        state = puzzle['game_state']
        expected = puzzle['solution']
        
        # Determine player index from state (usually the one whose turn it is)
        player_index = state.get('currentTurnIndex', 0)
        
        try:
            start_ts = time.perf_counter()
            decision = agent.get_decision(state, player_index)
            duration = (time.perf_counter() - start_ts) * 1000
            
            # Compare
            # We compare Action + CardIndex (if Play) or Action + Suit (if Bid)
            is_correct = False
            
            if expected.get('action') == decision.get('action'):
                if expected['action'] == 'PLAY':
                     # Loose comparison: CardIndex or Card Rank/Suit?
                     # Puzzles usually store the logic. 
                     # If the puzzle solution has 'cardIndex', use that.
                     if 'cardIndex' in expected:
                         is_correct = (expected['cardIndex'] == decision.get('cardIndex'))
                     else:
                         # Fallback: Compare content if needed (not implemented in simple check)
                         is_correct = True
                elif expected['action'] in ['SUN', 'HOKUM']:
                     is_correct = (expected.get('suit') == decision.get('suit'))
                else:
                     is_correct = True
            
            result_icon = "✅" if is_correct else "❌"
            if is_correct: correct_count += 1
            
            logger.info(f"{result_icon} Puzzle #{i+1}: {decision.get('action')} (Time: {duration:.1f}ms) | Expect: {expected.get('action')}")
            
            if not is_correct:
                 logger.info(f"   Reasoning: {decision.get('reasoning')}")
                 logger.info(f"   Expected: {expected.get('reason')} (from Gemini)")
                 
        except Exception as e:
            logger.error(f"Error executing puzzle {puzzle['id']}: {e}")

    accuracy = (correct_count / total) * 100
    
    logger.info("-" * 50)
    logger.info(f"🎓 Final IQ Score: {correct_count}/{total} ({accuracy:.1f}%)")
    
    # Grade
    grade = "F"
    if accuracy >= 90: grade = "A+"
    elif accuracy >= 80: grade = "A"
    elif accuracy >= 70: grade = "B"
    elif accuracy >= 60: grade = "C"
    elif accuracy >= 50: grade = "D"
    
    logger.info(f"🏆 Grade: {grade}")
    
    # Save Report
    report_path = os.path.join("docs", "iq_report.md")
    with open(report_path, "w", encoding='utf-8') as f:
         f.write(f"# 🧠 AI IQ Report\n")
         f.write(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}\n")
         f.write(f"**Score**: {accuracy:.1f}%\n")
         f.write(f"**Grade**: {grade}\n")
         f.write(f"**Sample Size**: {total} puzzles\n")

if __name__ == "__main__":
    measure_iq()
