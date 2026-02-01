from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from server.schemas.base import Suit, Rank

class CardModel(BaseModel):
    suit: Suit
    rank: Rank
    id: str
    value: int = 0

    model_config = ConfigDict(populate_by_name=True)

class DeckModel(BaseModel):
    cards: list[CardModel]
