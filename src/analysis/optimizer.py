from typing import List, Dict, Tuple
from src.models.player import Player
from src.models.team import Team
from src.analysis.predictor import FPLPredictor

class TransferOptimizer:
    MAX_PLAYERS_PER_TEAM = 3
    
    def __init__(self, predictor: FPLPredictor):
        self.predictor = predictor

    def _get_transfer_value(self, player_out: Player, player_in: Player, 
                          prediction_diff: float) -> float:
        """Calculate the value of a transfer"""
        price_diff = player_in.price - player_out.price
        if price_diff > 0:
            # Penalize expensive transfers slightly
            return prediction_diff - (price_diff * 0.5)
        return prediction_diff

    def suggest_transfers(self, team: Team, available_players: List[Player], 
                        num_weeks: int = 5) -> List[Dict]:
        """Suggest optimal transfers within budget and free transfer constraints"""
        suggestions = []
        remaining_budget = team.budget
        
        # Get predictions for current players
        current_predictions = {
            p.id: self.predictor.get_player_insights(p)
            for p in team.players
        }
        
        # Find potential transfer targets
        for player_out in team.players:
            position = player_out.position
            max_price = player_out.price + remaining_budget
            
            # Filter available players by position and price
            candidates = [
                p for p in available_players
                if p.position == position
                and p.price <= max_price
                and p.id not in [player.id for player in team.players]
            ]
            
            # Get predictions for candidates
            for player_in in candidates:
                prediction_in = self.predictor.get_player_insights(player_in)
                prediction_out = current_predictions[player_out.id]
                
                prediction_diff = (
                    prediction_in['predicted_points'] - 
                    prediction_out['predicted_points']
                )
                
                # Calculate transfer value considering price difference
                transfer_value = self._get_transfer_value(
                    player_out, player_in, prediction_diff
                )
                
                if transfer_value > 0:  # Only suggest beneficial transfers
                    suggestions.append({
                        'out': {
                            'name': player_out.name,
                            'team': player_out.team,
                            'price': player_out.price,
                            'predicted_points': prediction_out['predicted_points']
                        },
                        'in': {
                            'name': player_in.name,
                            'team': player_in.team,
                            'price': player_in.price,
                            'predicted_points': prediction_in['predicted_points'],
                            'form': player_in.form,
                            'fixtures': player_in.fixtures[:num_weeks],
                            'value_score': prediction_in['value_score']
                        },
                        'point_gain': prediction_diff,
                        'price_diff': player_in.price - player_out.price,
                        'transfer_value': transfer_value
                    })
        
        # Sort by transfer value and limit to free transfers
        suggestions.sort(key=lambda x: x['transfer_value'], reverse=True)
        return suggestions[:team.free_transfers]