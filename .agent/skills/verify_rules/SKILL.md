---
name: Verify Rules
description: Guide for verifying Baloot game logic and rules using the established test suite.
---

# Verify Rules Skill

This skill allows agents to efficiently verify that the game's core rule logic is functioning correctly. Use this when modifying `BiddingEngine`, `Game`, or `Bot Strategies`.

## 🧪 Test Matrix

| Feature | Test File | Description |
| :--- | :--- | :--- |
| **Bidding Logic** | `tests/test_bidding_rules.py` | Verifies Ashkal constraints, Kawesh (Redeal), Round 1/2 logic, and Doubling rules. |
| **Ashkal Rules** | `tests/test_ashkal_rules.py` | Specifically tests the complex eligibility rules for the "Ashkal" bid (Dealer/Partner/Round). |
| **Bot Brain** | `tests/test_bot_strategies.py` | Verifies the AI's decision making (Playing & Bidding), ensuring it respects rule constraints. |
| **Sawa (Sawa)** | `tests/test_sawa.py` | Verifies the "Claim All Tricks" mechanic and the voting/challenge system. |

## 🚀 How to Run Verification

Use the `python -m unittest` or `pytest` command.

### 1. Verify Everything (Recommended)
```powershell
python -m unittest discover tests
```

### 2. Verify Specific Rule Set
If you only touched the Bidding Engine:
```powershell
python -m unittest tests/test_bidding_rules.py
```

If you only touched the Bot:
```powershell
python -m unittest tests/test_bot_strategies.py
```

## ⚠️ Common Pitfalls

1.  **State Sync**: The `BiddingEngine` is often tested in isolation. If you use the `Game` wrapper in a test, ensure you sync state:
    ```python
    if game.bidding_engine:
         game.bidding_engine.floor_card = game.floor_card
    ```
2.  **Shared Constants**: Always import `BiddingPhase` and `BidType` from `game_engine.models.constants`, NOT from `server.bidding_engine`.
