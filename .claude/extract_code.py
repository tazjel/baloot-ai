"""Extract Python code blocks from Claude's response and save to staging.

Usage:
    python .claude/extract_code.py response.txt

Parses Claude's output for code blocks labeled with filenames (### filename.py)
and saves each to .claude/staging/filename.py.
"""
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STAGING = os.path.join(SCRIPT_DIR, "staging")

def extract_modules(text: str) -> list[tuple[str, str]]:
    """Extract (filename, code) pairs from Claude's markdown output."""
    # Pattern: ### optional_path/filename.py followed by ```python ... ```
    pattern = r'###\s+(?:\S+/)?(\w+\.py)\s*\n```python\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    if not matches:
        # Fallback: try without ### header, just ```python blocks with filename comment
        pattern2 = r'```python\n# File:\s*(\w+\.py)\n(.*?)```'
        matches = re.findall(pattern2, text, re.DOTALL)
    return matches

def main():
    if len(sys.argv) < 2:
        # Read from stdin if no file argument
        print("Paste Claude's response below (Ctrl+Z then Enter to finish):")
        text = sys.stdin.read()
    else:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            text = f.read()

    os.makedirs(STAGING, exist_ok=True)
    modules = extract_modules(text)

    if not modules:
        print("❌ No Python code blocks found!")
        print("   Expected format: ### filename.py followed by ```python ... ```")
        return

    print(f"✅ Extracted {len(modules)} modules:")
    for filename, code in modules:
        path = os.path.join(STAGING, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code.strip() + "\n")
        lines = len(code.strip().split("\n"))
        print(f"   → {filename} ({lines} lines) saved to staging/")

    print(f"\n   All files in: {STAGING}")
    print(f"   Next: ask Antigravity to review and integrate (use /delegate-to-claude)")

if __name__ == "__main__":
    main()
