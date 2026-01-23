---
description: Verify the game logic (Bidding, Ashkal, Bot, Sawa)
---

# Verify Game Logic

Run this workflow to ensure that the core game rules and bot strategies are working correctly.

1. Verify Bidding Engine Rules
```powershell
python -m unittest tests/test_bidding_rules.py
```

2. Verify Ashkal Rules (Complex Eligibility)
```powershell
python -m unittest tests/test_ashkal_rules.py
```

3. Verify Bot Strategies (AI Logic)
```powershell
python -m unittest tests/test_bot_strategies.py
```

4. Verify Sawa (ExternalApp) Logic
```powershell
python -m unittest tests/test_sawa.py
```
