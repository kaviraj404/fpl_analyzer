from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class PlayerPrediction:
    player_id: int
    gameweek: int
    predicted_points: float
    confidence_score: float
    form_score: float
    fixture_difficulty: float
    expected_goals: float
    expected_assists: float
    clean_sheet_probability: float
    minutes_probability: float
    prediction_date: datetime
    actual_points: Optional[float] = None