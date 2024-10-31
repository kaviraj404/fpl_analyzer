from flask import Flask, render_template, jsonify, request
import sys
import os
from pathlib import Path
from datetime import datetime

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
        
        players_data = []
        for element in fpl_data['elements']:
            prediction = db.get_prediction(element['id'], current_gameweek)
            games_played = max(1, element.get('appearances', 1))  # Avoid division by zero
            
            players_data.append({
                'id': element['id'],
                'name': element['web_name'],
                'team': next(t['name'] for t in fpl_data['teams'] if t['id'] == element['team']),
                'position': next(t['singular_name_short'] for t in fpl_data['element_types'] 
                               if t['id'] == element['element_type']),
                'price': element['now_cost'] / 10,
                'form': float(element['form'] or 0),
                'total_points': element['total_points'],
                'points_per_game': float(element['points_per_game'] or 0),
                'minutes': element['minutes'],
                'minutes_per_game': round(element['minutes'] / games_played, 1),
                'games_played': games_played,
                'predicted_points': prediction.predicted_points if prediction else 0,
                'selected_by': float(element['selected_by_percent'] or 0)
            })
        
        return jsonify({
            'data': players_data
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching players: {str(e)}")
        return jsonify({"error": str(e)}), 500

# app.py
@app.route('/player/<int:player_id>')
def player_details(player_id):
   try:
       fpl_data = FPLDataFetcher.fetch_all_data()
       player_history = FPLDataFetcher.fetch_player_history(player_id)
       db = Database(str(project_root / 'data' / 'fpl_data.db'))
       
       player_data = next(p for p in fpl_data['elements'] if p['id'] == player_id)
       prediction = db.get_prediction(player_id, current_gameweek)
       games_played = max(1, player_data.get('appearances', 1))
       
       recent_games = player_history['history'][-5:] if player_history.get('history') else []
       points_history = [g['total_points'] for g in recent_games]
       minutes_history = [g['minutes'] for g in recent_games]
       
       details = {
           'id': player_id,
           'name': player_data['web_name'],
           'team': next(t['name'] for t in fpl_data['teams'] if t['id'] == player_data['team']),
           'position': next(t['singular_name_short'] for t in fpl_data['element_types'] 
                          if t['id'] == player_data['element_type']),
           'price': player_data['now_cost'] / 10,
           'form': float(player_data['form'] or 0),
           'total_points': player_data['total_points'],
           'points_per_game': float(player_data['points_per_game'] or 0),
           'minutes_per_game': round(player_data['minutes'] / games_played, 1),
           'games_played': games_played,
           'predicted_points': prediction.predicted_points if prediction else 0,
           'selected_by': float(player_data['selected_by_percent'] or 0),
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