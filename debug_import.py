
try:
    print("Attempting to import ai_worker.strategies.playing...")
    from ai_worker.strategies.playing import PlayingStrategy
    print("SUCCESS: Imported PlayingStrategy")
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
