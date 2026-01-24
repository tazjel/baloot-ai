
import sys
import os
import traceback

sys.path.append(os.getcwd())

try:
    print("Attempting to import game_engine.logic.game...")
    from game_engine.logic.game import Game
    print("Import SUCCESS!")
except Exception:
    with open("import_error.log", "w") as f:
        traceback.print_exc(file=f)
    print("Import FAILED. Traceback written to import_error.log")
