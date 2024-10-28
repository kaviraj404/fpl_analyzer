from flask import Flask, render_template, jsonify, request
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.analyze_transfers import analyze_transfers

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get team_id from request data
        data = request.get_json()
        team_id = data.get('team_id')
        
        if not team_id:
            return jsonify({"success": False, "error": "Team ID is required"}), 400
            
        try:
            team_id = int(team_id)
        except ValueError:
            return jsonify({"success": False, "error": "Invalid team ID format"}), 400

        # Call analyze_transfers with the provided team_id
        result = analyze_transfers(team_id)
        
        if not result.get('success'):
            return jsonify(result), 400
            
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Analysis error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)