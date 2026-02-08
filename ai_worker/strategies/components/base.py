from abc import ABC, abstractmethod
from ai_worker.bot_context import BotContext


class StrategyComponent(ABC):
    """Abstract base class for all strategy components."""

    @abstractmethod
    def get_decision(self, ctx: BotContext) -> dict | None:
        """
        Returns a decision dict or None if no decision can be made.
        Decision format: {"action": "PLAY", "cardIndex": int, "reasoning": str}
        """
        ...
