
lines = []
with open('bot_agent.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines to delete: 408 to 478 (1-based index)
# Python list is 0-based.
# So delete index 407 to 478 (exclusive of 478? No 478 is included).
# Index 407 = Line 408.
# Index 477 = Line 478.
# Slice to keep: :407 + 478:

new_lines = lines[:407] + lines[478:]

with open('bot_agent.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Deleted lines 408-478. New line count: {len(new_lines)}")
