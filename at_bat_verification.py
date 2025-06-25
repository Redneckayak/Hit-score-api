"""
Simple at-bat verification for daily predictions
"""
import requests
import json
from datetime import date
from typing import Dict, List

def verify_player_at_bats(player_id: int, game_date: str = None) -> Dict:
    """Check if a player had at-bats on a specific date"""
    if game_date is None:
        game_date = date.today().isoformat()
    
    try:
        # Get games for the date
        response = requests.get(
            "https://statsapi.mlb.com/api/v1/schedule",
            params={'sportId': 1, 'date': game_date},
            timeout=10
        )
        
        if response.status_code != 200:
            return {'played': False, 'at_bats': 0, 'hits': 0}
        
        games_data = response.json()
        games = games_data.get('dates', [])
        
        if not games or not games[0].get('games'):
            return {'played': False, 'at_bats': 0, 'hits': 0}
        
        # Check each game for the player
        for game in games[0]['games']:
            game_id = game['gamePk']
            
            try:
                boxscore_response = requests.get(
                    f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore",
                    timeout=10
                )
                
                if boxscore_response.status_code != 200:
                    continue
                
                boxscore = boxscore_response.json()
                
                # Check both teams
                for team_type in ['away', 'home']:
                    team_data = boxscore.get('teams', {}).get(team_type, {})
                    batters = team_data.get('batters', [])
                    
                    if player_id in batters:
                        player_stats = team_data.get('players', {}).get(f'ID{player_id}', {})
                        batting_stats = player_stats.get('stats', {}).get('batting', {})
                        
                        at_bats = batting_stats.get('atBats', 0)
                        hits = batting_stats.get('hits', 0)
                        
                        return {
                            'played': at_bats > 0,
                            'at_bats': at_bats,
                            'hits': hits,
                            'got_hit': hits > 0 if at_bats > 0 else False
                        }
            
            except Exception:
                continue
        
        return {'played': False, 'at_bats': 0, 'hits': 0}
        
    except Exception as e:
        print(f"Error verifying player {player_id}: {e}")
        return {'played': False, 'at_bats': 0, 'hits': 0}

def update_predictions_with_at_bats(game_date: str = None):
    """Update predictions with actual at-bat verification"""
    if game_date is None:
        game_date = date.today().isoformat()
    
    try:
        # Load predictions
        with open('data/prediction_history.json', 'r') as f:
            predictions = json.load(f)
        
        if game_date not in predictions:
            print(f"No predictions found for {game_date}")
            return
        
        verified_predictions = {}
        removed_count = 0
        
        for player_id, prediction in predictions[game_date].items():
            verification = verify_player_at_bats(int(player_id), game_date)
            
            if verification['played']:
                # Player had at-bats, keep prediction and update with actual results
                verified_predictions[player_id] = prediction.copy()
                verified_predictions[player_id]['actual_hits'] = verification['hits']
                verified_predictions[player_id]['actual_at_bats'] = verification['at_bats']
                verified_predictions[player_id]['got_hit'] = verification['got_hit']
            else:
                # Player didn't have at-bats, remove from predictions
                removed_count += 1
                print(f"Removed {prediction['player_name']} ({prediction['team']}) - No at-bats")
        
        # Update predictions
        predictions[game_date] = verified_predictions
        
        with open('data/prediction_history.json', 'w') as f:
            json.dump(predictions, f, indent=2)
        
        print(f"Verified predictions for {game_date}: {len(verified_predictions)} kept, {removed_count} removed")
        
        # Update top 3 picks if any were removed
        if removed_count > 0:
            update_top_3_after_verification(game_date, verified_predictions)
        
        return {
            'verified_count': len(verified_predictions),
            'removed_count': removed_count
        }
        
    except Exception as e:
        print(f"Error updating predictions: {e}")
        return None

def update_top_3_after_verification(game_date: str, verified_predictions: Dict):
    """Update top 3 picks after removing players who didn't play"""
    try:
        with open('data/top_3_picks_history.json', 'r') as f:
            top_3_data = json.load(f)
        
        if game_date not in top_3_data:
            return
        
        # Get current top 3
        current_top_3 = top_3_data[game_date]
        updated_top_3 = {}
        rank = 1
        
        # Keep verified top 3 players
        for player_id, pick in current_top_3.items():
            if player_id in verified_predictions:
                updated_top_3[player_id] = verified_predictions[player_id].copy()
                updated_top_3[player_id]['rank'] = rank
                rank += 1
        
        # Fill remaining spots from verified predictions
        while len(updated_top_3) < 3 and len(verified_predictions) > len(updated_top_3):
            remaining_players = {
                pid: pred for pid, pred in verified_predictions.items() 
                if pid not in updated_top_3
            }
            
            if remaining_players:
                # Get highest scoring remaining player
                best_player = max(remaining_players.items(), key=lambda x: x[1]['hit_score'])
                player_id, prediction = best_player
                
                updated_top_3[player_id] = prediction.copy()
                updated_top_3[player_id]['rank'] = rank
                rank += 1
            else:
                break
        
        # Update top 3 picks
        top_3_data[game_date] = updated_top_3
        
        with open('data/top_3_picks_history.json', 'w') as f:
            json.dump(top_3_data, f, indent=2)
        
        print(f"Updated top 3 picks for {game_date}")
        
    except Exception as e:
        print(f"Error updating top 3: {e}")

if __name__ == "__main__":
    # Test for today
    result = update_predictions_with_at_bats()
    if result:
        print(f"Verification complete: {result}")