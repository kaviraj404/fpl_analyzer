import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict
from src.models.player import Player  # Changed from relative import

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
            c.executescript('''
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    team TEXT,
                    position TEXT,
                    price REAL,
                    total_points INTEGER,
                    form REAL,
                    timestamp DATETIME
                );

                CREATE TABLE IF NOT EXISTS predictions (
                    player_id INTEGER,
                    gameweek INTEGER,
                    predicted_points REAL,
                    timestamp DATETIME,
                    FOREIGN KEY(player_id) REFERENCES players(id)
                );
            ''')

    def save_players(self, players: List[Player]):
        with self.get_connection() as conn:
            c = conn.cursor()
            timestamp = datetime.now().isoformat()
            
            for player in players:
                c.execute('''
                    INSERT OR REPLACE INTO players 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    player.id, player.name, player.team,
                    player.position, player.price,
                    player.total_points, player.form,
                    timestamp
                ))