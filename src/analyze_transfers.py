import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from src.utils.data_fetcher import FPLDataFetcher
from src.utils.database import Database
from src.analysis.predictions import PredictionEngine
from src.config import DATABASE_PATH, LOG_FILE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def get_current_gameweek(events):
    """Get current gameweek from FPL data"""
    for event in events:
        if event['is_current']:
            return event['id']
    return 1

def analyze_transfers(team_id: int):
    """Analyze team and provide transfer recommendations"""
    try:
        # Initialize components
        db = Database(DATABASE_PATH)
        prediction_engine = PredictionEngine()
        
        # Fetch all FPL data
        logging.info(f"Fetching FPL data for team {team_id}...")
        fpl_data = FPLDataFetcher.fetch_all_data()
        
        # Fetch fixtures data
        logging.info("Fetching fixtures data...")
        fixtures_response = requests.get("https://fantasy.premierleague.com/api/fixtures/")
        fixtures_response.raise_for_status()
        fixtures_data = fixtures_response.json()
        
        # Get current gameweek
        current_gw = get_current_gameweek(fpl_data['events'])
        
        # Fetch team data using provided team_id
        logging.info(f"Fetching data for team ID: {team_id}")
        team_data = FPLDataFetcher.fetch_team_data(team_id)
        team_picks = FPLDataFetcher.fetch_team_picks(team_id, current_gw)
        
        if not team_data or not team_picks:
            raise ValueError(f"Could not find team with ID: {team_id}")
        
        # Get bank balance
        bank_balance = team_picks.get('entry_history', {}).get('bank', 0) / 10
        
        # Update predictions for all players
        logging.info("Updating predictions for all players...")
        all_predictions = []
        for element in fpl_data['elements']:
            player_history = FPLDataFetcher.fetch_player_history(element['id'])
            player = {
                'id': element['id'],
                'name': element['web_name'],
                'team': next(t['name'] for t in fpl_data['teams'] if t['id'] == element['team']),
                'position': next(p['singular_name_short'] for p in fpl_data['element_types'] 
                               if p['id'] == element['element_type']),
                'price': element['now_cost'] / 10,
                'form': float(element['form'] or 0),
                'points_per_game': float(element['points_per_game'] or 0),
                'selected_by': float(element['selected_by_percent'] or 0)
            }
            
            # Find next fixture for player
            team_id = element['team']
            next_fixture = next((f for f in fixtures_data 
                               if (f['team_h'] == team_id or f['team_a'] == team_id)
                               and not f.get('finished', True)), None)
            
            if next_fixture:
                prediction = prediction_engine.generate_prediction(
                    player,
                    player_history.get('history', []),
                    next_fixture,
                    current_gw
                )
                all_predictions.append(prediction)
        
        # Save predictions to database
        db.save_predictions_batch(all_predictions)
        
        # Get current squad with predictions
        current_squad = []
        squad_predictions = []
        for pick in team_picks['picks']:
            player_data = next(p for p in fpl_data['elements'] if p['id'] == pick['element'])
            prediction = db.get_prediction(player_data['id'], current_gw)
            
            player = {
                'id': player_data['id'],
                'name': player_data['web_name'],
                'team': next(t['name'] for t in fpl_data['teams'] if t['id'] == player_data['team']),
                'position': next(p['singular_name_short'] for p in fpl_data['element_types'] 
                               if p['id'] == player_data['element_type']),
                'price': player_data['now_cost'] / 10,
                'form': float(player_data['form'] or 0),
                'points_per_game': float(player_data['points_per_game'] or 0),
                'selected_by': float(player_data['selected_by_percent'] or 0),
                'prediction': prediction
            }
            current_squad.append(player)
            if prediction:
                squad_predictions.append(prediction)
        
        # Sort squad predictions for captain picks
        squad_predictions.sort(key=lambda x: x.predicted_points, reverse=True)
        captain_picks = squad_predictions[:3]
        
        # Get potential transfers
        # Get potential transfers
        transfer_suggestions = []
        
        # Get list of current player IDs in the squad
        current_squad_ids = [player['id'] for player in current_squad]

        for current_player in current_squad:
            # Find potential replacements
            position = current_player['position']
            max_price = current_player['price'] + bank_balance
            
            possible_replacements = [
                p for p in all_predictions
                if next((pl for pl in fpl_data['elements'] if pl['id'] == p.player_id), None) and
                next(pl for pl in fpl_data['elements'] if pl['id'] == p.player_id)['element_type'] == 
                next(t['id'] for t in fpl_data['element_types'] if t['singular_name_short'] == position) and
                next(pl for pl in fpl_data['elements'] if pl['id'] == p.player_id)['now_cost']/10 <= max_price and
                p.player_id != current_player['id'] and
                p.player_id not in current_squad_ids  # Exclude players already in squad
            ]
            
            # Sort replacements by predicted points
            possible_replacements.sort(key=lambda x: x.predicted_points, reverse=True)
            
            for replacement in possible_replacements[:3]:  # Top 3 replacements
                replacement_data = next(p for p in fpl_data['elements'] if p['id'] == replacement.player_id)
                
                # Calculate improvement metrics
                points_improvement = replacement.predicted_points - current_player['prediction'].predicted_points
                price_diff = replacement_data['now_cost']/10 - current_player['price']
                
                if points_improvement > 0:
                    transfer_suggestions.append({
                        'out': {
                            'player_id': current_player['id'],
                            'name': current_player['name'],
                            'team': current_player['team'],
                            'form': current_player['form'],
                            'price': current_player['price'],
                            'predicted_points': current_player['prediction'].predicted_points
                        },
                        'in': {
                            'player_id': replacement_data['id'],
                            'name': replacement_data['web_name'],
                            'team': next(t['name'] for t in fpl_data['teams'] if t['id'] == replacement_data['team']),
                            'form': float(replacement_data['form'] or 0),
                            'price': replacement_data['now_cost']/10,
                            'predicted_points': replacement.predicted_points,
                            'confidence': replacement.confidence_score,
                            'selected_by': float(replacement_data['selected_by_percent'] or 0)
                        },
                        'improvement': points_improvement,
                        'price_change': price_diff,
                        'remaining_budget': bank_balance - price_diff
                    })
        
        # Sort transfer suggestions by improvement
        transfer_suggestions.sort(key=lambda x: x['improvement'], reverse=True)
        
        return {
            'success': True,
            'team_status': {
                'name': team_data['name'],
                'overall_points': team_data['summary_overall_points'],
                'overall_rank': team_data['summary_overall_rank'],
                'bank_balance': bank_balance
            },
            'current_squad': [
                {
                    'player_id': player['id'],
                    'name': player['name'],
                    'team': player['team'],
                    'position': player['position'],
                    'price': player['price'],
                    'form': player['form'],
                    'predicted_points': player['prediction'].predicted_points if player['prediction'] else 0
                }
                for player in current_squad
            ],
            'captain_picks': [
                {
                    'player_id': pick.player_id,
                    'predicted_points': pick.predicted_points,
                    'confidence': pick.confidence_score,
                    'name': next(p['web_name'] for p in fpl_data['elements'] if p['id'] == pick.player_id),
                    'position': next(p['singular_name_short'] for p in fpl_data['element_types'] 
                                  if p['id'] == next(pl['element_type'] for pl in fpl_data['elements'] if pl['id'] == pick.player_id)),
                    'team': next(t['name'] for t in fpl_data['teams'] 
                               if t['id'] == next(pl['team'] for pl in fpl_data['elements'] if pl['id'] == pick.player_id))
                }
                for pick in captain_picks
            ],
            'transfer_suggestions': transfer_suggestions[:5],  # Top 5 transfer suggestions
            'predictions_updated': datetime.now().isoformat()
        }

    except Exception as e:
        logging.error(f"Error analyzing team {team_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    # For testing
    import json
    result = analyze_transfers(6044732)  # Replace with your team ID
    print(json.dumps(result, indent=2))