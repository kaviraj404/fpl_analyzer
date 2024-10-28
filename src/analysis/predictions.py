import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime
import logging
from src.models.prediction import PlayerPrediction

class PredictionEngine:
    def __init__(self):
        self.position_weights = {
            'GKP': {'clean_sheet': 4, 'save': 0.33, 'penalty_save': 5},
            'DEF': {'clean_sheet': 4, 'goal': 6, 'assist': 3},
            'MID': {'clean_sheet': 1, 'goal': 5, 'assist': 3},
            'FWD': {'goal': 4, 'assist': 3}
        }

    def calculate_form_metrics(self, player_history: List[Dict]) -> Dict:
        """Calculate form metrics based on recent games"""
        recent_games = player_history[-5:] if player_history else []
        
        if not recent_games:
            return {
                'avg_points': 0,
                'minutes_played': 0,
                'goals_scored': 0,
                'assists': 0,
                'clean_sheets': 0,
                'form_stability': 0
            }

        points = [g['total_points'] for g in recent_games]
        minutes = [g['minutes'] for g in recent_games]
        
        return {
            'avg_points': np.mean(points),
            'minutes_played': np.mean(minutes),
            'goals_scored': sum(g['goals_scored'] for g in recent_games),
            'assists': sum(g['assists'] for g in recent_games),
            'clean_sheets': sum(g['clean_sheets'] for g in recent_games),
            'form_stability': 1 - (np.std(points) / max(np.mean(points), 1))
        }

    def calculate_fixture_difficulty(self, fixture: Dict, is_home: bool) -> float:
        """Calculate fixture difficulty rating"""
        base_difficulty = fixture['team_h_difficulty'] if is_home else fixture['team_a_difficulty']
        home_advantage = 0.8 if is_home else 1.0
        return base_difficulty * home_advantage

    def predict_defensive_points(self, 
                               player: Dict, 
                               form_metrics: Dict, 
                               fixture_difficulty: float) -> Tuple[float, Dict]:
        """Predict points for defenders and goalkeepers"""
        position = player['position']
        weights = self.position_weights[position]
        
        # Calculate clean sheet probability
        clean_sheet_prob = max(0, 1 - (fixture_difficulty / 5)) * form_metrics['form_stability']
        
        # Base points (appearance + likely clean sheet)
        base_points = 2 + (clean_sheet_prob * weights['clean_sheet'])
        
        # Additional attacking threat for defenders
        if position == 'DEF':
            goal_prob = form_metrics['goals_scored'] / 5 * (1 - fixture_difficulty/5)
            assist_prob = form_metrics['assists'] / 5 * (1 - fixture_difficulty/5)
            base_points += (goal_prob * weights['goal'] + assist_prob * weights['assist'])
        
        return base_points, {
            'clean_sheet_probability': clean_sheet_prob,
            'expected_goals': goal_prob if position == 'DEF' else 0,
            'expected_assists': assist_prob if position == 'DEF' else 0
        }

    def predict_attacking_points(self, 
                               player: Dict, 
                               form_metrics: Dict, 
                               fixture_difficulty: float) -> Tuple[float, Dict]:
        """Predict points for midfielders and forwards"""
        weights = self.position_weights[player['position']]
        
        # Calculate goal probability
        goal_prob = (form_metrics['goals_scored'] / 5) * (1 - fixture_difficulty/5)
        
        # Calculate assist probability
        assist_prob = (form_metrics['assists'] / 5) * (1 - fixture_difficulty/5)
        
        # Base points calculation
        base_points = 2  # Appearance points
        base_points += goal_prob * weights['goal']
        base_points += assist_prob * weights['assist']
        
        if player['position'] == 'MID':
            clean_sheet_prob = max(0, 1 - (fixture_difficulty / 5)) * form_metrics['form_stability']
            base_points += clean_sheet_prob * weights['clean_sheet']
        else:
            clean_sheet_prob = 0
        
        return base_points, {
            'expected_goals': goal_prob,
            'expected_assists': assist_prob,
            'clean_sheet_probability': clean_sheet_prob
        }

    def calculate_confidence_score(self, 
                                 form_metrics: Dict, 
                                 fixture_difficulty: float) -> float:
        """Calculate confidence level of prediction"""
        minutes_factor = min(form_metrics['minutes_played'] / 90, 1)
        form_factor = form_metrics['form_stability']
        fixture_factor = 1 - (fixture_difficulty / 5)
        
        confidence = (minutes_factor * 0.4 + 
                     form_factor * 0.4 + 
                     fixture_factor * 0.2)
        
        return min(max(confidence, 0), 1)

    def generate_prediction(self, 
                          player: Dict, 
                          player_history: List[Dict], 
                          fixture: Dict,
                          gameweek: int) -> PlayerPrediction:
        """Generate complete prediction for a player"""
        form_metrics = self.calculate_form_metrics(player_history)
        is_home = fixture['team_h'] == player['team']
        fixture_difficulty = self.calculate_fixture_difficulty(fixture, is_home)
        
        # Calculate position-specific points
        if player['position'] in ['GKP', 'DEF']:
            base_points, probabilities = self.predict_defensive_points(
                player, form_metrics, fixture_difficulty
            )
        else:
            base_points, probabilities = self.predict_attacking_points(
                player, form_metrics, fixture_difficulty
            )
        
        # Calculate minutes probability
        minutes_prob = form_metrics['minutes_played'] / 90
        
        # Apply minutes probability to expected points
        predicted_points = base_points * minutes_prob
        
        # Calculate confidence score
        confidence_score = self.calculate_confidence_score(
            form_metrics, fixture_difficulty
        )
        
        return PlayerPrediction(
            player_id=player['id'],
            gameweek=gameweek,
            predicted_points=predicted_points,
            confidence_score=confidence_score,
            form_score=form_metrics['form_stability'],
            fixture_difficulty=fixture_difficulty,
            expected_goals=probabilities['expected_goals'],
            expected_assists=probabilities['expected_assists'],
            clean_sheet_probability=probabilities['clean_sheet_probability'],
            minutes_probability=minutes_prob,
            prediction_date=datetime.now(),
            actual_points=None
        )