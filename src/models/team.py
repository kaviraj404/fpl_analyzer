from dataclasses import dataclass
from typing import List
from src.models.player import Player  # Changed from relative import

@dataclass
class Team:
    budget: float
    players: List[Player]
    formation: str
    free_transfers: int