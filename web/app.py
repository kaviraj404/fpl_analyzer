from flask import Flask, render_template, jsonify, request
import sys
import os
from pathlib import Path
from datetime import datetime
import requests

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.analyze_transfers import analyze_transfers
from src.utils.data_fetcher import FPLDataFetcher
from src.utils.database import Database

app = Flask(__name__, 
           static_url_path='', 
           static_folder='static',
           template_folder='templates')

# Get current gameweek at app startup
def get_current_gameweek():
    try:
        fpl_data = FPLDataFetcher.fetch_all_data()
        for event in fpl_data['events']:
            if event['is_current']:
                return event['id']
        return 1
    except:
        return 1

current_gameweek = get_current_gameweek()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/players')
def players():
    return render_template('players.html')

@app.route('/methodology')
def methodology():
    return render_template('methodology.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        team_id = data.get('team_id')
        
        if not team_id:
            return jsonify({"success": False, "error": "Team ID is required"}), 400
            
        result = analyze_transfers(int(team_id))
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Analysis error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/players')
def get_all_players():
    try:
        fpl_data = FPLDataFetcher.fetch_all_data()
        db = Database(str(project_root / 'data' / 'fpl_data.db'))
        
        # Fetch fixtures data
        fixtures_response = requests.get("https://fantasy.premierleague.com/api/fixtures/")
        fixtures_response.raise_for_status()
        fixtures_data = fixtures_response.json()
        
        # Create a map of team ID to their next fixture
        team_next_fixtures = {}
        for fixture in fixtures_data:
            if not fixture.get('finished', True):  # Only consider upcoming fixtures
                home_team = fixture['team_h']
                away_team = fixture['team_a']
                
                # Add fixture for home team if they don't have one yet
                if home_team not in team_next_fixtures:
                    team_next_fixtures[home_team] = {
                        'opponent': next(t['short_name'] for t in fpl_data['teams'] if t['id'] == away_team),
                        'is_home': True
                    }
                
                # Add fixture for away team if they don't have one yet
                if away_team not in team_next_fixtures:
                    team_next_fixtures[away_team] = {
                        'opponent': next(t['short_name'] for t in fpl_data['teams'] if t['id'] == home_team),
                        'is_home': False
                    }
        
        players_data = []
        for element in fpl_data['elements']:
            prediction = db.get_prediction(element['id'], current_gameweek)
            
            try:
                player_history = FPLDataFetcher.fetch_player_history(element['id'])
                games_played = len([g for g in player_history.get('history', []) 
                                  if g['minutes'] > 0]) if player_history else 0
            except:
                games_played = max(1, element.get('appearances', 1))
            
            games_played = max(1, games_played)
            predicted_points = prediction.predicted_points if prediction else 0
            
            # Get next fixture information
            team_id = element['team']
            next_fixture = team_next_fixtures.get(team_id, {'opponent': '-', 'is_home': True})
            fixture_text = f"{next_fixture['opponent']} {'(H)' if next_fixture['is_home'] else '(A)'}"
            
            player_data = {
                'id': element['id'],
                'name': element['web_name'],
                'team': next(t['name'] for t in fpl_data['teams'] if t['id'] == element['team']),
                'position': next(t['singular_name_short'] for t in fpl_data['element_types'] 
                               if t['id'] == element['element_type']),
                'next_fixture': fixture_text,
                'price': round(element['now_cost'] / 10, 1),
                'form': round(float(element['form'] or 0), 1),
                'total_points': element['total_points'],
                'points_per_game': round(float(element['points_per_game'] or 0), 1),
                'minutes': element['minutes'],
                'minutes_per_game': round(element['minutes'] / games_played, 1),
                'games_played': games_played,
                'predicted_points': round(predicted_points),
                'selected_by': round(float(element['selected_by_percent'] or 0), 1)
            }
            
            players_data.append(player_data)
        
        players_data.sort(key=lambda x: x['total_points'], reverse=True)
        
        return jsonify({
            'data': players_data
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching players: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/player/<int:player_id>')
def player_details(player_id):
    try:
        fpl_data = FPLDataFetcher.fetch_all_data()
        player_history = FPLDataFetcher.fetch_player_history(player_id)
        db = Database(str(project_root / 'data' / 'fpl_data.db'))
        
        player_data = next(p for p in fpl_data['elements'] if p['id'] == player_id)
        prediction = db.get_prediction(player_id, current_gameweek)
        
        # Calculate actual games played
        games_played = len([g for g in player_history.get('history', []) 
                          if g['minutes'] > 0]) if player_history else 1
        games_played = max(1, games_played)  # Ensure no division by zero
        
        recent_games = player_history['history'][-5:] if player_history.get('history') else []
        points_history = [g['total_points'] for g in recent_games]
        minutes_history = [g['minutes'] for g in recent_games]
        
        details = {
            'id': player_id,
            'name': player_data['web_name'],
            'team': next(t['name'] for t in fpl_data['teams'] if t['id'] == player_data['team']),
            'position': next(t['singular_name_short'] for t in fpl_data['element_types'] 
                           if t['id'] == player_data['element_type']),
            'price': round(player_data['now_cost'] / 10, 1),
            'form': round(float(player_data['form'] or 0), 1),
            'total_points': player_data['total_points'],
            'points_per_game': round(float(player_data['points_per_game'] or 0), 1),
            'minutes_per_game': round(player_data['minutes'] / games_played, 1),
            'games_played': games_played,
            'predicted_points': round(prediction.predicted_points if prediction else 0),
            'selected_by': round(float(player_data['selected_by_percent'] or 0), 1),
            'recent_performance': {
                'points': points_history,
                'minutes': minutes_history,
                'goals': [g['goals_scored'] for g in recent_games],
                'assists': [g['assists'] for g in recent_games],
                'clean_sheets': [g['clean_sheets'] for g in recent_games],
                'bonus': [g['bonus'] for g in recent_games]
            }
        }
        
        return jsonify(details)
        
    except Exception as e:
        app.logger.error(f"Error fetching player details: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)