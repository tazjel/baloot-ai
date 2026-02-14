"""Bot personality profiles for bidding and playing behavior.

Each profile adjusts bidding thresholds and playing style.
Personalities are pure data — no logic, no cross-imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PersonalityProfile:
    """Bot personality that adjusts bidding thresholds and play style.

    Bidding Attributes:
        sun_bias: Adjust SUN threshold (positive = more aggressive)
        hokum_bias: Adjust HOKUM threshold (positive = more aggressive)
        ashkal_bias: Adjust ASHKAL threshold (positive = more aggressive)
        can_gamble: Allow risky bids on borderline hands

    Playing Attributes:
        trump_lead_bias: Preference for leading trumps (0.0=never, 1.0=always)
        point_greed: How aggressively to chase high-point tricks (0.0-1.0)
        risk_tolerance: Willingness to play risky cards (0.0=safe, 1.0=reckless)
        kaboot_pursuit: How early to commit to Kaboot sweep (0.0=never, 1.0=always)
        false_signal_rate: Chance of playing deceptive cards (0.0=honest, 1.0=always lie)
        partner_trust: How much to rely on partner signals (0.0=ignore, 1.0=full trust)
        doubling_confidence: Threshold multiplier for doubling (1.0=normal, 0.7=bold)

    Meta:
        name: Display name
        name_ar: Arabic display name
        description: Short description
        avatar_id: Avatar image identifier
        voice_lines: Speech lines for bot dialogue
    """
    name: str
    description: str
    # Bidding
    sun_bias: int = 0
    hokum_bias: int = 0
    ashkal_bias: int = 0
    can_gamble: bool = False
    # Playing
    trump_lead_bias: float = 0.5       # 0.0=avoid, 0.5=neutral, 1.0=prefer
    point_greed: float = 0.5           # 0.0=conservative, 1.0=greedy
    risk_tolerance: float = 0.5        # 0.0=safe, 1.0=reckless
    kaboot_pursuit: float = 0.3        # 0.0=never, 1.0=aggressive pursuit
    false_signal_rate: float = 0.0     # 0.0=honest, 1.0=deceptive
    partner_trust: float = 0.7         # 0.0=ignore, 1.0=full trust
    doubling_confidence: float = 1.0   # Multiplier for doubling threshold
    # Meta
    name_ar: str = ""
    avatar_id: str = "bot_1"
    voice_lines: Optional[List[str]] = None


# ═══════════════════════════════════════════════════════════════════
# Personality Presets
# ═══════════════════════════════════════════════════════════════════
# Bias > 0 means MORE likely to bid (Lower threshold)
# Bias < 0 means LESS likely to bid (Higher threshold)

BALANCED = PersonalityProfile(
    name="Saad",
    name_ar="سعد",
    description="Standard play style. No surprises.",
    sun_bias=0,
    hokum_bias=0,
    ashkal_bias=0,
    can_gamble=False,
    # Playing: neutral across the board
    trump_lead_bias=0.5,
    point_greed=0.5,
    risk_tolerance=0.5,
    kaboot_pursuit=0.3,
    false_signal_rate=0.0,
    partner_trust=0.7,
    doubling_confidence=1.0,
    avatar_id="avatar_saad",
    voice_lines=["Thinking...", "Let's play.", "Your turn."]
)

AGGRESSIVE = PersonalityProfile(
    name="Khalid",
    name_ar="خالد",
    description="Takes risks, bids on weaker hands, chases Kaboot.",
    sun_bias=3,    # Will bid Sun on 15 instead of 18
    hokum_bias=3,  # Will bid Hokum on 11 instead of 14
    ashkal_bias=2,
    can_gamble=True,
    # Playing: bold, greedy, trump-happy
    trump_lead_bias=0.8,       # Loves leading trumps
    point_greed=0.8,           # Chases high-point tricks
    risk_tolerance=0.8,        # Willing to take risks
    kaboot_pursuit=0.7,        # Commits to Kaboot at 5+ tricks
    false_signal_rate=0.0,     # Honest but aggressive
    partner_trust=0.5,         # Trusts own judgment more
    doubling_confidence=0.7,   # Doubles more readily
    avatar_id="avatar_khalid",
    voice_lines=["I'm going for it!", "Hokum!", "All in!"]
)

CONSERVATIVE = PersonalityProfile(
    name="Abu Fahad",
    name_ar="أبو فهد",
    description="Plays safe, only bids on strong hands, protects points.",
    sun_bias=-3,   # Will bid Sun on 21
    hokum_bias=-2, # Will bid Hokum on 16
    ashkal_bias=-2,
    can_gamble=False,
    # Playing: safe, defensive, point-protective
    trump_lead_bias=0.3,       # Avoids leading trumps (saves them)
    point_greed=0.3,           # Protects existing points
    risk_tolerance=0.2,        # Very safe plays
    kaboot_pursuit=0.1,        # Rarely chases Kaboot
    false_signal_rate=0.0,     # Completely honest
    partner_trust=0.8,         # High trust in partner
    doubling_confidence=1.3,   # Requires more certainty to double
    avatar_id="avatar_abu_fahad",
    voice_lines=["Too risky.", "Pass.", "Not this time."]
)

TRICKY = PersonalityProfile(
    name="Majed",
    name_ar="ماجد",
    description="Deceptive play. False signals, underplays early, surprises late.",
    sun_bias=1,    # Slightly aggressive bids
    hokum_bias=1,
    ashkal_bias=1,
    can_gamble=True,
    # Playing: deceptive, unpredictable
    trump_lead_bias=0.4,       # Sometimes leads trump, sometimes not
    point_greed=0.6,           # Moderate greed
    risk_tolerance=0.6,        # Moderate risk
    kaboot_pursuit=0.4,        # Opportunistic Kaboot
    false_signal_rate=0.3,     # 30% chance of deceptive play
    partner_trust=0.5,         # Mixed trust (hard to read)
    doubling_confidence=0.9,   # Slightly bold on doubling
    avatar_id="avatar_majed",
    voice_lines=["Hmm...", "Watch this.", "Surprise!"]
)


PROFILES = {
    'Balanced': BALANCED,
    'Aggressive': AGGRESSIVE,
    'Conservative': CONSERVATIVE,
    'Tricky': TRICKY,
}
