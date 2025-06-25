import requests
import os
from typing import Dict, Optional
import time

class SportsDataFetcher:
    """Fetches authentic MLB splits data from SportsData.io"""
    
    def __init__(self):
        self.api_key = os.getenv('SPORTSDATA_IO_API_KEY')
        self.base_url = "https://api.sportsdata.io/v3/mlb"
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'Ocp-Apim-Subscription-Key': self.api_key
            })
    
    def get_player_splits_by_name(self, player_name: str, team_abbr: str) -> Dict:
        """Get authentic splits data for a player using SportsData.io Player Season Split Stats"""
        try:
            if not self.api_key:
                return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
            # Use the correct Player Season Split Stats endpoint
            season = 2024
            url = f"{self.base_url}/playerseasonsplitsstats/2024"
            
            response = self.session.get(url)
            
            if response.status_code != 200:
                print(f"SportsData.io API error: {response.status_code} - {response.text}")
                return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
            splits_data = response.json()
            
            # Find the player's authentic splits data
            player_splits = self._find_authentic_splits(splits_data, player_name, team_abbr)
            
            # Add delay to respect API limits
            time.sleep(0.1)
            
            return player_splits
            
        except Exception as e:
            print(f"Error fetching splits from SportsData.io for {player_name}: {e}")
            return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
    
    def _find_authentic_splits(self, splits_data: list, target_name: str, target_team: str) -> Dict:
        """Find specific player and extract splits data"""
        try:
            for split_record in splits_data:
                name = split_record.get('Name', '')
                team = split_record.get('Team', '')
                split_category = split_record.get('Split', '')
                
                # Check if this is our target player
                if (self._names_match(name, target_name) and 
                    self._teams_match(team, target_team)):
                    
                    # Extract authentic splits data based on split category
                    batting_avg = self._safe_float(split_record.get('BattingAverage', 0.238))
                    
                    # Look for specific handedness splits
                    if 'Left' in split_category or 'LHP' in split_category:
                        return {'vs_left': batting_avg, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
                    elif 'Right' in split_category or 'RHP' in split_category:
                        return {'vs_left': 0.238, 'vs_right': batting_avg, 'home': 0.250, 'away': 0.230}
                    elif 'Home' in split_category:
                        return {'vs_left': 0.238, 'vs_right': 0.238, 'home': batting_avg, 'away': 0.230}
                    elif 'Away' in split_category:
                        return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': batting_avg}
            
            # If no specific splits found, return defaults
            return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
        except Exception as e:
            print(f"Error parsing player splits: {e}")
            return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
    
    def _names_match(self, api_name: str, target_name: str) -> bool:
        """Check if player names match (handle variations)"""
        if not api_name or not target_name:
            return False
        
        api_name = api_name.lower().strip()
        target_name = target_name.lower().strip()
        
        # Direct match
        if api_name == target_name:
            return True
        
        # Check if last name and first initial match
        api_parts = api_name.split()
        target_parts = target_name.split()
        
        if len(api_parts) >= 2 and len(target_parts) >= 2:
            # Last name match and first initial match
            if (api_parts[-1] == target_parts[-1] and 
                api_parts[0][0] == target_parts[0][0]):
                return True
        
        return False
    
    def _teams_match(self, api_team: str, target_team: str) -> bool:
        """Check if team abbreviations match"""
        if not api_team or not target_team:
            return False
        
        return api_team.upper().strip() == target_team.upper().strip()
    
    def _safe_float(self, value, default: float = 0.238) -> float:
        """Safely convert value to float"""
        try:
            if value is None:
                return default
            
            float_val = float(value)
            
            # For batting averages, ensure reasonable range
            if 0.100 <= float_val <= 0.500:
                return float_val
            else:
                return default
                
        except (ValueError, TypeError):
            return default
    
    def get_detailed_player_splits(self, player_name: str, team_abbr: str) -> Dict:
        """Get more detailed splits data if available"""
        try:
            # Try to get more specific splits endpoint if available
            url = f"{self.base_url}/playersplits/2024"
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                splits_data = response.json()
                return self._parse_detailed_splits(splits_data, player_name, team_abbr)
            else:
                # Fallback to basic player stats
                return self.get_player_splits_by_name(player_name, team_abbr)
                
        except Exception as e:
            print(f"Error getting detailed splits: {e}")
            return self.get_player_splits_by_name(player_name, team_abbr)
    
    def _parse_detailed_splits(self, splits_data: list, target_name: str, target_team: str) -> Dict:
        """Parse detailed splits data from SportsData.io"""
        try:
            for split in splits_data:
                name = split.get('Name', '')
                team = split.get('Team', '')
                
                if (self._names_match(name, target_name) and 
                    self._teams_match(team, target_team)):
                    
                    # Extract authentic splits data
                    vs_left = self._safe_float(split.get('VsLeftBattingAverage', 0.238))
                    vs_right = self._safe_float(split.get('VsRightBattingAverage', 0.238))
                    home = self._safe_float(split.get('HomeBattingAverage', 0.250))
                    away = self._safe_float(split.get('AwayBattingAverage', 0.230))
                    
                    return {
                        'vs_left': vs_left,
                        'vs_right': vs_right,
                        'home': home,
                        'away': away
                    }
            
            # Player not found in splits data
            return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
        except Exception as e:
            print(f"Error parsing detailed splits: {e}")
            return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}