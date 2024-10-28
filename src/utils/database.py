import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Optional
from src.models.player import Player
from src.models.prediction import PlayerPrediction

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.setup_database()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def setup_database(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Create players table
            c.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    team TEXT,
                    position TEXT,
                    price REAL,
                    total_points INTEGER,
                    form REAL,
                    timestamp DATETIME
                )
            ''')

            # Create predictions table
            c.execute('''
                CREATE TABLE IF NOT EXISTS player_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    gameweek INTEGER,
                    predicted_points REAL,
                    confidence_score REAL,
                    form_score REAL,
                    fixture_difficulty REAL,
                    expected_goals REAL,
                    expected_assists REAL,
                    clean_sheet_probability REAL,
                    minutes_probability REAL,
                    prediction_date TIMESTAMP,
                    actual_points REAL,
                    FOREIGN KEY(player_id) REFERENCES players(id),
                    UNIQUE(player_id, gameweek)
                )
            ''')

            # Create fixtures table
            c.execute('''
                CREATE TABLE IF NOT EXISTS fixtures (
                    id INTEGER PRIMARY KEY,
                    gameweek INTEGER,
                    home_team TEXT,
                    away_team TEXT,
                    difficulty_score REAL,
                    timestamp DATETIME
                )
            ''')
            
            # Create indices for faster lookups
            c.execute('CREATE INDEX IF NOT EXISTS idx_player_gameweek ON player_predictions(player_id, gameweek)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_fixture_gameweek ON fixtures(gameweek)')
            
            conn.commit()

    def save_players(self, players: List[Player]):
        """Save or update player data"""
        with self.get_connection() as conn:
            c = conn.cursor()
            timestamp = datetime.now().isoformat()
            
            for player in players:
                c.execute('''
                    INSERT OR REPLACE INTO players 
                    (id, name, team, position, price, total_points, form, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    player.id,
                    player.name,
                    player.team,
                    player.position,
                    player.price,
                    player.total_points,
                    player.form,
                    timestamp
                ))
            
            conn.commit()

    def save_prediction(self, prediction: PlayerPrediction):
        """Save or update a player prediction"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO player_predictions (
                    player_id, gameweek, predicted_points, confidence_score,
                    form_score, fixture_difficulty, expected_goals, expected_assists,
                    clean_sheet_probability, minutes_probability, prediction_date, actual_points
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                prediction.player_id,
                prediction.gameweek,
                prediction.predicted_points,
                prediction.confidence_score,
                prediction.form_score,
                prediction.fixture_difficulty,
                prediction.expected_goals,
                prediction.expected_assists,
                prediction.clean_sheet_probability,
                prediction.minutes_probability,
                prediction.prediction_date.isoformat(),
                prediction.actual_points
            ))
            conn.commit()

    def save_predictions_batch(self, predictions: List[PlayerPrediction]):
        """Save multiple predictions at once"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.executemany('''
                INSERT OR REPLACE INTO player_predictions (
                    player_id, gameweek, predicted_points, confidence_score,
                    form_score, fixture_difficulty, expected_goals, expected_assists,
                    clean_sheet_probability, minutes_probability, prediction_date, actual_points
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [(
                p.player_id, p.gameweek, p.predicted_points, p.confidence_score,
                p.form_score, p.fixture_difficulty, p.expected_goals, p.expected_assists,
                p.clean_sheet_probability, p.minutes_probability,
                p.prediction_date.isoformat(), p.actual_points
            ) for p in predictions])
            conn.commit()

    def get_player(self, player_id: int) -> Optional[Player]:
        """Get player data by ID"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM players WHERE id = ?', (player_id,))
            row = c.fetchone()
            
            if row:
                return Player(
                    id=row[0],
                    name=row[1],
                    team=row[2],
                    position=row[3],
                    price=row[4],
                    total_points=row[5],
                    form=row[6]
                )
            return None

    def get_all_players(self) -> List[Player]:
        """Get all players"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM players')
            
            return [Player(
                id=row[0],
                name=row[1],
                team=row[2],
                position=row[3],
                price=row[4],
                total_points=row[5],
                form=row[6]
            ) for row in c.fetchall()]

    def get_prediction(self, player_id: int, gameweek: int) -> Optional[PlayerPrediction]:
        """Get prediction for a specific player and gameweek"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT * FROM player_predictions 
                WHERE player_id = ? AND gameweek = ?
            ''', (player_id, gameweek))
            
            row = c.fetchone()
            if row:
                return PlayerPrediction(
                    player_id=row[1],
                    gameweek=row[2],
                    predicted_points=row[3],
                    confidence_score=row[4],
                    form_score=row[5],
                    fixture_difficulty=row[6],
                    expected_goals=row[7],
                    expected_assists=row[8],
                    clean_sheet_probability=row[9],
                    minutes_probability=row[10],
                    prediction_date=datetime.fromisoformat(row[11]),
                    actual_points=row[12]
                )
            return None

    def get_gameweek_predictions(self, gameweek: int) -> List[PlayerPrediction]:
        """Get all predictions for a specific gameweek"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM player_predictions WHERE gameweek = ?', (gameweek,))
            
            return [PlayerPrediction(
                player_id=row[1],
                gameweek=row[2],
                predicted_points=row[3],
                confidence_score=row[4],
                form_score=row[5],
                fixture_difficulty=row[6],
                expected_goals=row[7],
                expected_assists=row[8],
                clean_sheet_probability=row[9],
                minutes_probability=row[10],
                prediction_date=datetime.fromisoformat(row[11]),
                actual_points=row[12]
            ) for row in c.fetchall()]

    def update_actual_points(self, player_id: int, gameweek: int, actual_points: float):
        """Update actual points after gameweek completion"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                UPDATE player_predictions 
                SET actual_points = ? 
                WHERE player_id = ? AND gameweek = ?
            ''', (actual_points, player_id, gameweek))
            conn.commit()

    def get_prediction_accuracy(self, gameweek: int) -> Dict:
        """Calculate prediction accuracy for a completed gameweek"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT 
                    AVG(ABS(predicted_points - actual_points)) as avg_error,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(*) as total_predictions
                FROM player_predictions 
                WHERE gameweek = ? AND actual_points IS NOT NULL
            ''', (gameweek,))
            
            row = c.fetchone()
            return {
                'average_error': row[0],
                'average_confidence': row[1],
                'total_predictions': row[2]
            }

    def cleanup_old_predictions(self, keep_weeks: int = 10):
        """Remove predictions older than specified number of gameweeks"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                DELETE FROM player_predictions 
                WHERE gameweek < (
                    SELECT MAX(gameweek) - ? FROM player_predictions
                )
            ''', (keep_weeks,))
            conn.commit()