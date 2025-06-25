"""
Player verification system to ensure all listed players actually have at-bats
"""
import requests
from datetime import date
from typing import Dict, List, Optional
import json

class PlayerVerification:
    """Verifies that players actually played and had at-bats"""
    
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1"
    
    def get_player_game_stats(self, player_id: int, game_date: str = None) -> Optional[Dict]:
        """Get player's actual game stats for a specific date"""
        if game_date is None:
            game_date = date.today().isoformat()
        
        try:
            # Get games for the date
            games_response = requests.get(
                f"{self.base_url}/schedule",
                params={'sportId': 1, 'date': game_date},
                timeout=10
            )
            
            if games_response.status_code != 200:
                return None
                
            games_data = games_response.json()
            games = games_data.get('dates', [])
            
            if not games or not games[0].get('games'):
                return None
            
            # Find player's game
            for game in games[0]['games']:
                game_id = game['gamePk']
                
                # Get box score for this game
                boxscore_response = requests.get(
                    f"{self.base_url}/game/{game_id}/boxscore",
                    timeout=10
                )
                
                if boxscore_response.status_code != 200:
                    continue
                
                boxscore = boxscore_response.json()
                
                # Check both teams for the player
                for team_type in ['away', 'home']:
                    team_data = boxscore.get('teams', {}).get(team_type, {})
                    batters = team_data.get('batters', [])
                    
                    if player_id in batters:
                        # Found the player, get their stats
                        player_stats = team_data.get('players', {}).get(f'ID{player_id}', {})
                        batting_stats = player_stats.get('stats', {}).get('batting', {})
                        
                        return {
                            'player_id': player_id,
                            'game_date': game_date,
                            'game_id': game_id,
                            'at_bats': batting_stats.get('atBats', 0),
                            'hits': batting_stats.get('hits', 0),
                            'played': batting_stats.get('atBats', 0) > 0
                        }
            
            return None
            
        except Exception as e:
            print(f"Error verifying player {player_id}: {e}")
            return None
    
    def verify_predictions(self, predictions: Dict, game_date: str = None) -> Dict:
        """Verify that all predicted players actually played"""
        if game_date is None:
            game_date = date.today().isoformat()
        
        verified_predictions = {}
        removed_players = []
        
        for player_id, prediction in predictions.items():
            player_stats = self.get_player_game_stats(int(player_id), game_date)
            
            if player_stats and player_stats['played']:
                # Player played, keep prediction and update with actual stats
                verified_predictions[player_id] = prediction.copy()
                verified_predictions[player_id]['actual_hits'] = player_stats['hits']
                verified_predictions[player_id]['actual_at_bats'] = player_stats['at_bats']
                verified_predictions[player_id]['got_hit'] = player_stats['hits'] > 0
            else:
                # Player didn't play, remove from predictions
                removed_players.append({
                    'player_id': player_id,
                    'player_name': prediction.get('player_name', 'Unknown'),
                    'team': prediction.get('team', 'Unknown'),
                    'hit_score': prediction.get('hit_score', 0)
                })
        
        return {
            'verified_predictions': verified_predictions,
            'removed_players': removed_players,
            'verification_date': game_date
        }
    
    def update_predictions_with_verification(self, game_date: str = None) -> Dict:
        """Update prediction files with verification"""
        if game_date is None:
            game_date = date.today().isoformat()
        
        try:
            # Load predictions
            with open('data/prediction_history.json', 'r') as f:
                all_predictions = json.load(f)
            
            if game_date not in all_predictions:
                return {'error': f'No predictions found for {game_date}'}
            
            # Verify predictions
            verification_result = self.verify_predictions(all_predictions[game_date], game_date)
            
            # Update predictions with verified data
            all_predictions[game_date] = verification_result['verified_predictions']
            
            # Save updated predictions
            with open('data/prediction_history.json', 'w') as f:
                json.dump(all_predictions, f, indent=2)
            
            # Update top 3 picks if needed
            if verification_result['removed_players']:
                self._update_top_3_after_verification(game_date, verification_result)
            
            return {
                'verified_count': len(verification_result['verified_predictions']),
                'removed_count': len(verification_result['removed_players']),
                'removed_players': verification_result['removed_players'],
                'game_date': game_date
            }
            
        except Exception as e:
            return {'error': f'Verification failed: {e}'}
    
    def _update_top_3_after_verification(self, game_date: str, verification_result: Dict):
        """Update top 3 picks after removing players who didn't play"""
        try:
            # Load top 3 picks
            with open('data/top_3_picks_history.json', 'r') as f:
                top_3_data = json.load(f)
            
            if game_date not in top_3_data:
                return
            
            # Check if any top 3 players were removed
            current_top_3 = top_3_data[game_date]
            verified_predictions = verification_result['verified_predictions']
            removed_player_ids = [p['player_id'] for p in verification_result['removed_players']]
            
            updated_top_3 = {}
            rank = 1
            
            # Keep verified top 3 players
            for player_id, pick in current_top_3.items():
                if player_id not in removed_player_ids and player_id in verified_predictions:
                    updated_top_3[player_id] = verified_predictions[player_id].copy()
                    updated_top_3[player_id]['rank'] = rank
                    rank += 1
            
            # Fill remaining spots from verified predictions
            while len(updated_top_3) < 3 and len(verified_predictions) >= rank:
                # Find next highest scoring verified player not already in top 3
                remaining_players = {
                    pid: pred for pid, pred in verified_predictions.items() 
                    if pid not in updated_top_3
                }
                
                if remaining_players:
                    # Sort by hit score and take the highest
                    sorted_remaining = sorted(
                        remaining_players.items(), 
                        key=lambda x: x[1]['hit_score'], 
                        reverse=True
                    )
                    
                    next_player_id, next_prediction = sorted_remaining[0]
                    updated_top_3[next_player_id] = next_prediction.copy()
                    updated_top_3[next_player_id]['rank'] = rank
                    rank += 1
                else:
                    break
            
            # Update top 3 picks
            top_3_data[game_date] = updated_top_3
            
            with open('data/top_3_picks_history.json', 'w') as f:
                json.dump(top_3_data, f, indent=2)
                
        except Exception as e:
            print(f"Error updating top 3 after verification: {e}")

def verify_daily_predictions(game_date: str = None):
    """Convenience function to verify daily predictions"""
    verifier = PlayerVerification()
    return verifier.update_predictions_with_verification(game_date)

if __name__ == "__main__":
    # Test verification for today
    result = verify_daily_predictions()
    print(f"Verification result: {result}")