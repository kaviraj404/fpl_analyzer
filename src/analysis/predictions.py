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

    def calculate_form_metrics(self, player_history: List[Dict], player: Dict) -> Dict:
        """Calculate form metrics considering both recent and season-long performance"""
        recent_games = player_history[-5:] if player_history else []
        
        if not recent_games:
            return {
                'avg_points': 0,
                'minutes_played': 0,
                'goals_scored': 0,
                'assists': 0,
                'clean_sheets': 0,
                'form_stability': 0,
                'season_ppg': 0,
                'total_games': 0
            }

        # Season performance metrics
        total_games = len(player_history)
        season_points_per_game = sum(g['total_points'] for g in player_history) / total_games if total_games > 0 else 0
        
        # Recent form with weighted last 5 games
        weights = [0.1, 0.15, 0.2, 0.25, 0.3]  # Most recent games count more
        points = [g['total_points'] for g in recent_games]
        weighted_recent_form = sum(p * w for p, w in zip(points, weights[-len(points):]))
        
        # Combine recent form with season performance
        combined_form = (weighted_recent_form * 0.6) + (season_points_per_game * 0.4)
        
        return {
            'avg_points': combined_form,
            'season_ppg': season_points_per_game,
            'minutes_played': np.mean([g['minutes'] for g in recent_games]),
            'goals_scored': sum(g['goals_scored'] for g in recent_games),
            'assists': sum(g['assists'] for g in recent_games),
            'clean_sheets': sum(g['clean_sheets'] for g in recent_games),
            'form_stability': 1 - (np.std(points) / max(combined_form, 1)),
            'total_games': total_games
        }

    def calculate_fixture_difficulty(self, fixture: Dict, is_home: bool) -> float:
        """Calculate fixture difficulty rating with reduced impact"""
        base_difficulty = fixture['team_h_difficulty'] if is_home else fixture['team_a_difficulty']
        home_advantage = 0.9 if is_home else 1.0  # Reduced home advantage impact
        return (base_difficulty * home_advantage) * 0.8  # Reduced overall fixture impact

    def predict_defensive_points(self, 
                               player: Dict, 
                               form_metrics: Dict, 
                               fixture_difficulty: float) -> Tuple[float, Dict]:
        """Predict points for defenders and goalkeepers"""
        position = player['position']
        weights = self.position_weights[position]
        
        # Clean sheet probability weighted by season performance
        clean_sheet_base = max(0, 1 - (fixture_difficulty / 5))
        season_factor = min(form_metrics['season_ppg'] / 4, 1)  # Normalized by typical clean sheet points
        clean_sheet_prob = clean_sheet_base * form_metrics['form_stability'] * (0.7 + (0.3 * season_factor))
        
        # Base points calculation
        base_points = 2 + (clean_sheet_prob * weights['clean_sheet'])
        
        return base_points, {
            'clean_sheet_probability': clean_sheet_prob,
            'expected_goals': 0,
            'expected_assists': 0
        }

    def predict_attacking_points(self, 
                               player: Dict, 
                               form_metrics: Dict, 
                               fixture_difficulty: float) -> Tuple[float, Dict]:
        """Predict points for midfielders and forwards"""
        weights = self.position_weights[player['position']]
        
        # Adjust probabilities based on season performance
        season_factor = min(form_metrics['season_ppg'] / 6, 1)  # Normalized by typical good performance
        
        # Calculate goal probability
        goal_prob = ((form_metrics['goals_scored'] / 5) * 0.6 + 
                    (form_metrics['season_ppg'] / 10) * 0.4) * (1 - fixture_difficulty/5)
        
        # Calculate assist probability
        assist_prob = ((form_metrics['assists'] / 5) * 0.6 + 
                      (form_metrics['season_ppg'] / 15) * 0.4) * (1 - fixture_difficulty/5)
        
        # Base points calculation
        base_points = 2  # Appearance points
        base_points += goal_prob * weights['goal']
        base_points += assist_prob * weights['assist']
        
        if player['position'] == 'MID':
            clean_sheet_prob = max(0, 1 - (fixture_difficulty / 5)) * form_metrics['form_stability'] * 0.5
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
        season_factor = min(form_metrics['season_ppg'] / 6, 1)  # Added season performance factor
        fixture_factor = 1 - (fixture_difficulty / 5)
        
        confidence = (minutes_factor * 0.3 + 
                     form_factor * 0.3 + 
                     season_factor * 0.2 +
                     fixture_factor * 0.2)
        
        return min(max(confidence, 0), 1)

    def generate_prediction(self, 
                          player: Dict, 
                          player_history: List[Dict], 
                          fixture: Dict,
                          gameweek: int) -> PlayerPrediction:
        """Generate complete prediction for a player"""
        form_metrics = self.calculate_form_metrics(player_history, player)
        is_home = fixture['team_h'] == player['team']
        fixture_difficulty = self.calculate_fixture_difficulty(fixture, is_home)
        
        # Calculate base prediction
        if player['position'] in ['GKP', 'DEF']:
            base_points, probabilities = self.predict_defensive_points(
                player, form_metrics, fixture_difficulty
            )
        else:
            base_points, probabilities = self.predict_attacking_points(
                player, form_metrics, fixture_difficulty
            )
        
        # Adjust prediction based on season performance
        season_factor = form_metrics['season_ppg'] / max(base_points, 1)
        adjusted_points = base_points * (0.7 + (0.3 * season_factor))
        
        # Minutes probability adjustment
        minutes_prob = form_metrics['minutes_played'] / 90
        
        # Final prediction combining all factors
        predicted_points = adjusted_points * minutes_prob
        
        # Weight prediction more heavily towards season performance for consistent top performers
        if form_metrics['total_games'] > 5 and form_metrics['season_ppg'] > 5:
            predicted_points = (predicted_points * 0.7) + (form_metrics['season_ppg'] * 0.3)
        
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