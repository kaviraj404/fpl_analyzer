import numpy as np
from typing import List, Dict
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from src.models.player import Player

class FPLPredictor:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False

    def _create_feature_vector(self, player: Player) -> List[float]:
        """Create a feature vector for a player"""
        recent_minutes = player.minutes[-5:] if player.minutes else [0] * 5
        recent_goals = player.goals[-5:] if player.goals else [0] * 5
        recent_assists = player.assists[-5:] if player.assists else [0] * 5
        recent_clean_sheets = player.clean_sheets[-5:] if player.clean_sheets else [0] * 5

        features = [
            player.form,
            np.mean(recent_minutes),
            np.mean(recent_goals),
            np.mean(recent_assists),
            np.mean(recent_clean_sheets),
            player.price,
            len([f for f in player.fixtures if f.get('is_home', False)]) / max(len(player.fixtures), 1),  # Home game ratio
            np.mean([f.get('difficulty', 3) for f in player.fixtures]) if player.fixtures else 3,  # Avg difficulty
        ]
        return features

    def train(self, players: List[Player]):
        """Train the prediction model"""
        X = []  # Features
        y = []  # Target (points)

        for player in players:
            if player.total_points > 0:  # Only use players who have played
                X.append(self._create_feature_vector(player))
                y.append(player.total_points)

        if not X:
            raise ValueError("No valid training data found")

        X = np.array(X)
        y = np.array(y)

        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True

    def predict_points(self, player: Player) -> Dict:
        """Predict points for a player"""
        if not self.is_trained:
            raise ValueError("Model needs to be trained first")

        features = self._create_feature_vector(player)
        features_scaled = self.scaler.transform([features])
        predicted_points = self.model.predict(features_scaled)[0]

        return {
            'player_id': player.id,
            'name': player.name,
            'predicted_points': round(predicted_points, 2),
            'form': player.form,
            'price': player.price,
            'position': player.position,
        }

    def get_player_insights(self, player: Player) -> Dict:
        """Get detailed insights for a player"""
        prediction = self.predict_points(player)
        recent_minutes = player.minutes[-5:] if player.minutes else []
        
        insights = {
            **prediction,
            'minutes_trend': 'Consistent' if recent_minutes and np.std(recent_minutes) < 15 else 'Irregular',
            'rotation_risk': 'High' if recent_minutes and np.mean(recent_minutes) < 60 else 'Low',
            'form_trend': 'Improving' if player.form > 5 else 'Declining',
            'value_score': round(prediction['predicted_points'] / player.price, 2),
            'upcoming_fixtures': [
                {
                    'difficulty': f.get('difficulty', 3),
                    'is_home': f.get('is_home', False)
                } for f in player.fixtures[:5]
            ]
        }
        return insights