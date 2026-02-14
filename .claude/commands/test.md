Run the test suite and report results:

```bash
python -m pytest tests/bot/ tests/game_logic/ --tb=short -q
```

If tests fail, read the failing test and the source file it tests. Diagnose whether it's a test bug or source bug. Report findings but do NOT auto-fix unless I ask.
