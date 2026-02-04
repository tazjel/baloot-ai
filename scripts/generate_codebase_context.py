import os
import fnmatch
from typing import List, Set

# 🚀 CONFIGURATION
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FULL = os.path.join(PROJECT_ROOT, "claude_context_FULL.txt")
OUTPUT_LITE = os.path.join(PROJECT_ROOT, "claude_context_LITE.txt")

# 🚫 EXCLUSIONS (Save Tokens!)
EXCLUDE_DIRS = {
    ".git", ".env", "node_modules", "logs", "__pycache__", "venv", 
    "dist", "build", "coverage", "htmlcov", ".pytest_cache", ".mypy_cache",
    "ai_training", "models", "static", "docs", ".agent", ".gemini"
}

EXCLUDE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".mp4", ".mp3", ".wav",
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".bin", ".pkl", ".joblib",
    ".pt", ".pth", ".onnx", ".db", ".sqlite", ".log", ".csv", ".tsv",
    ".lock", ".map", ".min.js", ".min.css", ".pdf", ".docx", ".zip"
}

# 📏 SIZE LIMIT (Files larger than this are skipped to save tokens)
MAX_FILE_SIZE_KB = 50 
LITE_MODE_MAX_KB = 10 # Strict limit for Lite mode

# 🧠 SMART CONTEXT PATTERNS (Files to prioritized/injected at top)
PRIORITY_FILES = [
    "README.md",
    "current_state.md",
    "architecture.md", 
    "developer_tips.md",
    "handoff.md",
    "task.md",
    "CODEBASE_MAP.md"
]

def load_gitignore_patterns(root):
    """Load gitignore patterns into a simple list."""
    patterns = []
    gitignore_path = os.path.join(root, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    return patterns

def is_ignored(path, patterns):
    """Simple fnmatch check for gitignore patterns."""
    name = os.path.basename(path)
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(path, pattern):
            return True
    return False

def get_file_tree(root_path, exclude_dirs, patterns) -> str:
    """Generates a visual tree of the codebase."""
    tree_lines = ["\n# 🌳 PROJECT STRUCTURE (File Tree)\n"]
    
    for root, dirs, files in os.walk(root_path):
        # Filter dirs in-place
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
        
        level = root.replace(root_path, '').count(os.sep)
        indent = ' ' * 4 * level
        subindent = ' ' * 4 * (level + 1)
        
        # Don't print root
        if root != root_path:
            tree_lines.append(f"{indent}{os.path.basename(root)}/")
            
        for f in files:
            rel_path = os.path.relpath(os.path.join(root, f), root_path)
            if not is_ignored(rel_path, patterns):
                 # Check extension
                _, ext = os.path.splitext(f)
                if ext.lower() not in EXCLUDE_EXTENSIONS:
                    tree_lines.append(f"{subindent}{f}")
                    
    tree_lines.append("\n" + "="*50 + "\n")
    return "\n".join(tree_lines)

def find_priority_files(root_path) -> List[tuple]:
    """Scans for high-value docs to inject at the top."""
    found = []
    # 1. Check local root
    for fname in PRIORITY_FILES:
        path = os.path.join(root_path, fname)
        if os.path.exists(path):
             found.append((fname, path))
    
    # 2. Check .agent/knowledge (common pattern)
    knowledge_path = os.path.join(root_path, ".agent", "knowledge")
    if os.path.exists(knowledge_path):
         for f in os.listdir(knowledge_path):
             if f in PRIORITY_FILES or f.endswith("_tips.md"):
                  found.append((f"knowledge/{f}", os.path.join(knowledge_path, f)))
                  
    return found

def generate_snapshots():
    print(f"🚀 Generating Smart Context from: {PROJECT_ROOT}")
    patterns = load_gitignore_patterns(PROJECT_ROOT)
    
    # 1. Generate Tree
    print("   🌳 Building File Tree...")
    file_tree = get_file_tree(PROJECT_ROOT, EXCLUDE_DIRS, patterns)
    
    # 2. Find Priority Context
    print("   🧠 Hunting for Knowledge artifacts...")
    priority_docs = find_priority_files(PROJECT_ROOT)
    
    # 3. Generate FULL and LITE snapshots
    modes = [
        ("FULL", OUTPUT_FULL, MAX_FILE_SIZE_KB), 
        ("LITE", OUTPUT_LITE, LITE_MODE_MAX_KB)
    ]
    
    for mode_name, output_path, max_size in modes:
        file_count = 0
        token_est = 0
        
        with open(output_path, "w", encoding="utf-8") as out:
            # HEADER
            out.write(f"# BALOOT AI: {mode_name} CONTEXT SNAPSHOT\n")
            out.write(f"# Generated for Claude Desktop. Mode: {mode_name}\n\n")
            
            # INJECT PRIORITY DOCS
            if priority_docs:
                out.write("# 🧠 CRITICAL CONTEXT (Read This First)\n\n")
                for name, path in priority_docs:
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                        out.write(f"### DOC: {name}\n")
                        out.write(content + "\n\n")
                        token_est += len(content) / 4
                    except: pass
            
            # INJECT TREE
            out.write(file_tree)
            token_est += len(file_tree) / 4
            
            # INJECT FILES
            out.write(f"\n# 📝 SOURCE CODE (Max Size: {max_size}KB)\n\n")
            
            for root, dirs, files in os.walk(PROJECT_ROOT):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]

                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, PROJECT_ROOT)
                    
                    if is_ignored(rel_path, patterns): continue
                    
                    _, ext = os.path.splitext(file)
                    if ext.lower() in EXCLUDE_EXTENSIONS: continue
                    
                    # Logic: Only include file content if it passes filters
                    # In LITE mode, we might skip implementation files unless they are small
                    
                    size_kb = os.path.getsize(file_path) / 1024
                    
                    # Skip logic
                    if size_kb > max_size:
                        out.write(f"### FILE: {rel_path} (SKIPPED - >{max_size}KB)\n")
                        continue
                        
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        out.write(f"### FILE: {rel_path}\n")
                        out.write("```" + ext.replace(".", "") + "\n")
                        out.write(content)
                        out.write("\n```\n\n")
                        file_count += 1
                        token_est += len(content) / 4
                    except: pass

        print(f"   ✅ {mode_name} Snapshot: {os.path.basename(output_path)} ({int(token_est)} tokens)")

    print("\n💡 TIP: Use 'FULL' for deep coding tasks. Use 'LITE' for architecture questions.")

if __name__ == "__main__":
    generate_snapshots()

