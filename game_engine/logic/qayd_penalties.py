"""
Qayd Penalties - Penalty Calculation Logic
==========================================

Handles the calculation of points and penalties for Qayd outcomes.
Separated from the engine to keep logic focused.
"""

class QaydPenaltyCalculator:
    """Calculates penalty points based on game mode and doubling."""

    @staticmethod
    def calculate_base_penalty(game_mode: str, doubling_level: int) -> int:
        """
        Calculate base penalty points.
        
        SUN/ASHKAL = 26 base
        HOKUM = 16 base
        Multiplied by doubling level.
        """
        mode_str = str(game_mode or '').upper()
        is_sun = ('SUN' in mode_str) or ('ASHKAL' in mode_str)
        base = 26 if is_sun else 16

        dl = doubling_level if doubling_level else 1
        if dl >= 2:
            base *= dl

        return base

    @staticmethod
    def calculate_total_penalty(base_penalty: int, project_points: int) -> int:
        """
        Total penalty includes base penalty plus any declared project points.
        """
        return base_penalty + project_points
