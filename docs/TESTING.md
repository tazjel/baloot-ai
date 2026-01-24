# Testing & Debugging Guide

This project includes a suite of tools to help you verify changes and debug issues.

## Workflows

We use a workflow system to run common tasks. You can run these via the chat interface (e.g., "Run test all").

| Command | Description |
|---|---|
| `/test-all` | Runs **Backend Simulations** + **Frontend Unit Tests**. |
| `/debug-last-game` | Automatically finds the latest log and checks for lag/errors. |
| `/ask-bot` | Interactive tool to input a hand and ask the bot "What would you play?". |

## Manual Tools

### `run_test_suite.py`
Runs backend simulation scenarios defined in `test_scenarios.py`.
```bash
python run_test_suite.py
```

### `scripts/analyze_logs.py`
Analyze server logs for performance issues.
```bash
python scripts/analyze_logs.py --file logs/my_log.log
# OR
python scripts/analyze_logs.py --latest
```

## Adding New Tests

- **Backend**: Add new scenario classes to `server/test_scenarios.py` and register them in `run_test_suite.py`.
- **Frontend**: Add `.test.ts` or `.test.tsx` files alongside your components. `vitest` picks them up automatically.
