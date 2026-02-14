Trace a hypothetical play decision through the AI brain cascade.

Ask me for:
1. Mode (SUN or HOKUM)
2. Hand cards (e.g., "A♠ 10♠ K♥ 7♥ J♦ 8♦ Q♣ 9♣")
3. Table cards (what's been played this trick, or empty if leading)
4. Game context (tricks won by us, are we buyers, trump suit if HOKUM)

Then trace through:
- brain.py's 7-step cascade (which steps activate, what they recommend)
- lead_selector.py strategies (if leading)
- follow_optimizer.py tactics (if following)

Show the full decision path with confidence scores. This helps debug bot AI decisions.
