from dataclasses import dataclass

@dataclass
class PersonalityProfile:
    name: str
    description: str
    sun_bias: int = 0
    hokum_bias: int = 0
    ashkal_bias: int = 0
    can_gamble: bool = False
    avatar_id: str = "bot_1" # Default avatar
    voice_lines: list = None

# Presets
# Bias > 0 means MORE likely to bid (Lower threshold)
# Bias < 0 means LESS likely to bid (Higher threshold)

BALANCED = PersonalityProfile(
    name="Saad",
    description="Standard play style.",
    sun_bias=0,
    hokum_bias=0,
    ashkal_bias=0,
    can_gamble=False,
    avatar_id="avatar_saad",
    voice_lines=["Thinking...", "Let's play."]
)

AGGRESSIVE = PersonalityProfile(
    name="Khalid",
    description="Takes risks, bids on weaker hands.",
    sun_bias=3,    # Will bid Sun on 15 instead of 18
    hokum_bias=3,  # Will bid Hokum on 11 instead of 14
    ashkal_bias=2,
    can_gamble=True,
    avatar_id="avatar_khalid",
    voice_lines=["I'm going for it!", "Hokum!"]
)

CONSERVATIVE = PersonalityProfile(
    name="Abu Fahad",
    description="Plays safe, only bids on strong hands.",
    sun_bias=-3,   # Will bid Sun on 21
    hokum_bias=-2, # Will bid Hokum on 16
    ashkal_bias=-2,
    can_gamble=False,
    avatar_id="avatar_abu_fahad",
    voice_lines=["Too risky.", "Pass."]
)

PROFILES = {
    'Balanced': BALANCED,
    'Aggressive': AGGRESSIVE,
    'Conservative': CONSERVATIVE
}
