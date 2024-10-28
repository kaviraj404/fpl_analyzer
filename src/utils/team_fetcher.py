import requests
import logging
from typing import Dict, List, Tuple
from src.models.player import Player
from src.models.team import Team

class TeamFetcher:
    def __init__(self, team_id: int):
        self.team_id = team_id
        self.session = requests.Session()

    def login(self, email: str, password: str) -> bool:
        """Login to FPL to access private team data"""
        try:
            # FPL login URLs
            login_url = "https://users.premierleague.com/accounts/login/"
            
            # Headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
            }
            self.session.headers.update(headers)

            # Get login page first to get cookies
            self.session.get(login_url)

            # Prepare login payload
            payload = {
                'password': password,
                'login': email,
                'redirect_uri': 'https://fantasy.premierleague.com/accounts/login/',
                'app': 'plfpl-web'
            }

            # Add required headers for login request
            login_headers = {
                'Origin': 'https://users.premierleague.com',
                'Referer': 'https://users.premierleague.com/accounts/login/',
            }

            # Perform login
            response = self.session.post(
                login_url,
                data=payload,
                headers={**headers, **login_headers}
            )

            # Verify login success
            if 'sessionid' in self.session.cookies:
                logging.info("Login successful")
                return True
            else:
                logging.error("Login failed - no session cookie received")
                return False

        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            return False

    def get_team_data(self) -> Dict:
        """Fetch team data including players, budget, and transfers"""
        try:
            # First get the entry data
            entry_url = f"https://fantasy.premierleague.com/api/my-team/{self.team_id}/"
            response = self.session.get(entry_url)
            
            if response.status_code == 404:
                raise Exception("Team not found. Check your team ID.")
            elif response.status_code == 401:
                raise Exception("Unauthorized. Login required.")
            
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logging.error(f"Error fetching team data: {str(e)}")
            raise

    def get_current_team(self) -> Tuple[Team, float, int]:
        """Get current team, remaining budget, and free transfers"""
        team_data = self.get_team_data()
        
        # Get basic team info
        transfers = team_data.get('transfers', {})
        free_transfers = transfers.get('limit', 1)
        budget = team_data.get('transfers', {}).get('bank', 0) / 10  # Convert to millions

        # Get player details
        picks = team_data.get('picks', [])
        player_ids = [p['element'] for p in picks]
        
        # Fetch general data once
        general_response = requests.get(
            "https://fantasy.premierleague.com/api/bootstrap-static/"
        )
        general_response.raise_for_status()
        general_data = general_response.json()
        
        # Get player details
        players = []
        for player_id in player_ids:
            try:
                # Get player history
                player_response = requests.get(
                    f"https://fantasy.premierleague.com/api/element-summary/{player_id}/"
                )
                player_response.raise_for_status()
                player_history = player_response.json()
                
                # Find player in general data
                player_data = next(
                    p for p in general_data['elements'] 
                    if p['id'] == player_id
                )
                
                players.append(Player.from_api_response(player_data, player_history))
                
            except Exception as e:
                logging.error(f"Error fetching player {player_id}: {str(e)}")
                continue

        team = Team(
            budget=budget,
            players=players,
            formation="",  # We don't need formation for transfer analysis
            free_transfers=free_transfers
        )
        
        return team, budget, free_transfers