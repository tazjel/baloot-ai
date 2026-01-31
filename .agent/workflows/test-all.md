---
description: Run all tests (frontend and backend) for the Baloot game.
---

This workflow runs the full suite of backend simulation scenarios and frontend unit tests.

1. Run Backend Scenarios
```bash
python scripts/run_test_suite.py
```

2. Run Frontend Unit Tests
```bash
cd frontend
npm test
```
