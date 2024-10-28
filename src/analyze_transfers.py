import logging
import requests
from src.utils.data_fetcher import FPLDataFetcher
from src.analysis.predictor import FPLPredictor
from src.analysis.optimizer import TransferOptimizer
from src.config import LOG_FILE

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
    return 1  # Default to 1 if not found

def predict_next_week_points(player, fpl_data, fixtures_data):
    """Predict points for next gameweek based on form, fixture difficulty, and position"""
    try:
        # Get player's team ID
        team_id = next(t['id'] for t in fpl_data['teams'] 
                      if t['name'] == player['team'])
        
        # Get next fixture difficulty
        next_fixture = next((f for f in fixtures_data 
                           if (f['team_h'] == team_id or f['team_a'] == team_id)
                           and not f.get('finished', True)), None)
        
        if not next_fixture:
            # If no fixture found, return based on form only
            return float(player['points_per_game']) * float(player['form']) / 5, None
        
        is_home = next_fixture['team_h'] == team_id
        difficulty = next_fixture['team_h_difficulty'] if is_home else next_fixture['team_a_difficulty']
        
        # Calculate predicted points
        base_prediction = float(player['points_per_game'])
        form_factor = float(player['form']) / 5  # Scale form impact
        difficulty_factor = (6 - difficulty) / 5  # Convert difficulty to positive factor
        home_advantage = 1.1 if is_home else 1.0
        
        predicted_points = base_prediction * form_factor * difficulty_factor * home_advantage
        
        return predicted_points, next_fixture

    except Exception as e:
        logging.error(f"Error predicting points for {player['name']}: {str(e)}")
        return float(player['points_per_game']), None

def get_best_transfers(current_squad, all_players, bank_balance, num_suggestions=5):
    """Get the most impactful transfers considering budget constraints"""
    potential_transfers = []
    
    for current_player in current_squad:
        max_price = current_player['price'] + bank_balance  # Maximum affordable price
        
        # Filter available players by position and affordability
        position_players = [
            p for p in all_players
            if p['position'] == current_player['position']
            and p['price'] <= max_price
            and p['name'] != current_player['name']  # Exclude same player
        ]
        
        for new_player in position_players:
            form_improvement = float(new_player['form']) - float(current_player['form'])
            points_improvement = float(new_player['points_per_game']) - float(current_player['points_per_game'])
            price_diff = new_player['price'] - current_player['price']
            
            # Enhanced transfer score calculation
            transfer_score = (
                (form_improvement * 2) +  # Form weighted heavily
                (points_improvement * 3) +  # Points per game is key
                (min(0, price_diff) * 0.5)  # Small bonus for saving money
            )
            
            # Only include transfers with positive impact
            if transfer_score > 0:
                potential_transfers.append({
                    'out': current_player,
                    'in': new_player,
                    'score': transfer_score,
                    'form_improvement': form_improvement,
                    'points_improvement': points_improvement,
                    'price_diff': price_diff,
                    'remaining_budget': bank_balance - price_diff
                })
    
    # Sort by transfer score and get top suggestions
    potential_transfers.sort(key=lambda x: x['score'], reverse=True)
    return potential_transfers[:num_suggestions]

def analyze_transfers(team_id):
    try:
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
        bank_balance = team_picks.get('entry_history', {}).get('bank', 0) / 10  # Convert to millions
        
        # Get current squad
        current_squad = []
        for pick in team_picks['picks']:
            player_data = next(p for p in fpl_data['elements'] if p['id'] == pick['element'])
            current_squad.append({
                'name': player_data['web_name'],
                'team': next(t['name'] for t in fpl_data['teams'] if t['id'] == player_data['team']),
                'position': next(p['singular_name_short'] for p in fpl_data['element_types'] 
                               if p['id'] == player_data['element_type']),
                'price': player_data['now_cost'] / 10,
                'form': float(player_data['form'] or 0),
                'points_per_game': float(player_data['points_per_game'] or 0),
                'selected_by': float(player_data['selected_by_percent'] or 0)
            })
        
        # Get captain options
        captain_options = []
        for player in current_squad:
            predicted_points, next_fixture = predict_next_week_points(player, fpl_data, fixtures_data)
            
            if next_fixture:
                # Get opponent name
                team_id = next(t['id'] for t in fpl_data['teams'] if t['name'] == player['team'])
                is_home = next_fixture['team_h'] == team_id
                opponent_id = next_fixture['team_a'] if is_home else next_fixture['team_h']
                opponent_name = next(t['name'] for t in fpl_data['teams'] if t['id'] == opponent_id)
            else:
                is_home = False
                opponent_name = "No fixture found"
            
            captain_options.append({
                'name': player['name'],
                'predicted_points': predicted_points,
                'form': player['form'],
                'opponent': opponent_name,
                'is_home': is_home,
                'position': player['position']
            })
        
        # Sort captain options by predicted points
        captain_options.sort(key=lambda x: x['predicted_points'], reverse=True)

        # Get all players for comparison
        all_players = []
        for element in fpl_data['elements']:
            team_name = next(t['name'] for t in fpl_data['teams'] if t['id'] == element['team'])
            position = next(p['singular_name_short'] for p in fpl_data['element_types'] 
                          if p['id'] == element['element_type'])
            
            all_players.append({
                'id': element['id'],
                'name': element['web_name'],
                'team': team_name,
                'position': position,
                'price': element['now_cost'] / 10,
                'form': float(element['form'] or 0),
                'points_per_game': float(element['points_per_game'] or 0),
                'total_points': element['total_points'],
                'selected_by': float(element['selected_by_percent'] or 0)
            })

        # Get best possible transfers
        best_transfers = get_best_transfers(current_squad, all_players, bank_balance)

        return {
            'success': True,
            'team_status': {
                'name': team_data['name'],
                'overall_points': team_data['summary_overall_points'],
                'overall_rank': team_data['summary_overall_rank'],
                'bank_balance': bank_balance
            },
            'current_squad': current_squad,
            'captain_picks': captain_options[:3],  # Top 3 captain options
            'transfer_suggestions': best_transfers,
            'considerations': {
                'inactive_players': any(p['form'] == 0 for p in current_squad),
                'out_of_form_players': any(float(p['form']) < 2 for p in current_squad)
            }
        }

    except Exception as e:
        logging.error(f"Error analyzing team {team_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    # For command line testing
    import json
    result = analyze_transfers(6044732)  # Test with a specific team ID
    print(json.dumps(result, indent=2))