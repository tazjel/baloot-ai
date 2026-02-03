
import subprocess
import os

try:
    with open('logs/verify_output.txt', 'w', encoding='utf-8') as f:
        subprocess.call(['python', 'tests/verify_sherlock_logic.py'], stdout=f, stderr=subprocess.STDOUT)
    print("Verification complete. Check logs/verify_output.txt")
except Exception as e:
    print(f"Error: {e}")
