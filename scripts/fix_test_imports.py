import os

TESTS_DIR = 'tests'

REPLACEMENTS = {
    'from server.bidding_engine': 'from game_engine.logic.bidding_engine',
    'import server.bidding_engine': 'import game_engine.logic.bidding_engine',
    'from server.bot_agent': 'from ai_worker.agent',
    'import server.bot_agent': 'import ai_worker.agent',
    'from bot_agent': 'from ai_worker.agent', # Case where server was in path
    'import bot_agent': 'import ai_worker.agent',
    'from server.bot_memory': 'from ai_worker.memory',
    'from bot_memory': 'from ai_worker.memory',
    'from server.game_engine': 'from game_engine.logic.game', # Assuming Logic exists
}

def fix_imports():
    count = 0
    for root, dirs, files in os.walk(TESTS_DIR):
        for file in files:
            if not file.endswith('.py'):
                continue
            
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            modified = False
            for old, new in REPLACEMENTS.items():
                if old in new_content:
                    new_content = new_content.replace(old, new)
                    modified = True
            
            if modified:
                print(f"Fixing {path}...")
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                count += 1
    
    print(f"Fixed {count} files.")

if __name__ == '__main__':
    fix_imports()
