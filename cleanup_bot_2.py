
lines = []
with open('bot_agent.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines to delete: 555 to 577 (1-based index)
# Python list slice: [:554] + [577:]
# Index 554 = Line 555.
# Index 577 = Line 578.

new_lines = lines[:554] + lines[577:]

with open('bot_agent.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Deleted lines 555-577. New line count: {len(new_lines)}")
