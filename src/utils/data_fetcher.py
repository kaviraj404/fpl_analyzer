import requests
import logging
from typing import Dict, List
from src.models.player import Player

class FPLDataFetcher:
    BASE_URL = "https://fantasy.premierleague.com/api"

    @classmethod
    def fetch_all_data(cls) -> Dict:
        """Fetch all FPL data in one call"""
        try:
            response = requests.get(f"{cls.BASE_URL}/bootstrap-static/")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error fetching FPL data: {str(e)}")
            raise

    @classmethod
    def fetch_team_data(cls, team_id: int) -> Dict:
        """Fetch data for a specific team"""
        try:
            response = requests.get(f"{cls.BASE_URL}/entry/{team_id}/")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error fetching team data: {str(e)}")
            raise

    @classmethod
    def fetch_team_picks(cls, team_id: int, gameweek: int) -> Dict:
        """Fetch team picks for a specific gameweek"""
        try:
            response = requests.get(f"{cls.BASE_URL}/entry/{team_id}/event/{gameweek}/picks/")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error fetching team picks: {str(e)}")
            raise

    @classmethod
    def fetch_player_history(cls, player_id: int) -> Dict:
        """Fetch detailed history for a player"""
        try:
            response = requests.get(f"{cls.BASE_URL}/element-summary/{player_id}/")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error fetching player history: {str(e)}")
            raise