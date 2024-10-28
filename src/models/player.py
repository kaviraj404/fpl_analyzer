from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Player:
    id: int
    name: str
    team: str
    position: str
    price: float
    total_points: int
    form: float
    minutes: List[int]
    goals: List[int]
    assists: List[int]
    clean_sheets: List[int]
    fixtures: List[Dict]

    @classmethod
    def from_api_response(cls, data: Dict, history: Dict):
        # Map element_type to position string
        position_map = {
            1: 'GK',
            2: 'DEF',
            3: 'MID',
            4: 'FWD'
        }

        return cls(
            id=data['id'],
            name=data['web_name'],
            team=data['team'],
            position=position_map.get(data['element_type'], 'MID'),  # Default to MID if unknown
            price=data['now_cost'] / 10,
            total_points=data['total_points'],
            form=float(data['form'] or 0),  # Handle None values
            minutes=[g['minutes'] for g in history['history'][-5:]] if history.get('history') else [0] * 5,
            goals=[g['goals_scored'] for g in history['history'][-5:]] if history.get('history') else [0] * 5,
            assists=[g['assists'] for g in history['history'][-5:]] if history.get('history') else [0] * 5,
            clean_sheets=[g['clean_sheets'] for g in history['history'][-5:]] if history.get('history') else [0] * 5,
            fixtures=history.get('fixtures', [])[:5]
        )