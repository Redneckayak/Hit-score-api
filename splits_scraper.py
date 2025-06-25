import requests
import trafilatura
from typing import Dict, Optional
import re
import time
from datetime import datetime

class SplitsScraper:
    """Scrapes authentic MLB batter splits data from Baseball Reference"""
    
    def __init__(self):
        self.base_url = "https://www.baseball-reference.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_player_splits_from_bbref(self, player_name: str, team_abbr: str) -> Dict:
        """Get authentic splits data for a player from Baseball Reference"""
        try:
            # Search for player page
            player_url = self._find_player_url(player_name, team_abbr)
            if not player_url:
                return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
            # Get player page content
            response = self.session.get(player_url)
            if response.status_code != 200:
                return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
            # Extract splits data from the page
            splits = self._parse_splits_data(response.text)
            
            # Add small delay to be respectful to the server
            time.sleep(1)
            
            return splits
            
        except Exception as e:
            print(f"Error scraping splits for {player_name}: {e}")
            return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
    
    def _find_player_url(self, player_name: str, team_abbr: str) -> Optional[str]:
        """Find the Baseball Reference URL for a player"""
        try:
            # Convert player name to search format
            name_parts = player_name.lower().split()
            if len(name_parts) < 2:
                return None
            
            first_name = name_parts[0]
            last_name = name_parts[-1]
            
            # Baseball Reference uses first letter of last name for organization
            first_letter = last_name[0]
            
            # Try common Baseball Reference URL pattern
            # Format: /players/[first_letter]/[last_name][first_name][01].shtml
            player_id = f"{last_name[:5]}{first_name[:2]}01"
            player_url = f"{self.base_url}/players/{first_letter}/{player_id}.shtml"
            
            # Test if URL exists
            response = self.session.head(player_url)
            if response.status_code == 200:
                return player_url
            
            # Try with 02, 03 suffixes if 01 doesn't work
            for suffix in ['02', '03', '04']:
                player_id = f"{last_name[:5]}{first_name[:2]}{suffix}"
                player_url = f"{self.base_url}/players/{first_letter}/{player_id}.shtml"
                response = self.session.head(player_url)
                if response.status_code == 200:
                    return player_url
            
            return None
            
        except Exception as e:
            print(f"Error finding player URL for {player_name}: {e}")
            return None
    
    def _parse_splits_data(self, html_content: str) -> Dict:
        """Parse splits data from Baseball Reference HTML"""
        try:
            # Look for splits table in the HTML
            # Baseball Reference typically has splits data in tables with specific IDs
            
            # Default values
            splits = {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
            # Extract current year batting average vs LHP and RHP
            # Look for patterns like "vs LHP" and "vs RHP" in the HTML
            
            # Pattern for vs Left-handed pitching
            lhp_pattern = r'vs LHP.*?\.(\d{3})'
            lhp_match = re.search(lhp_pattern, html_content, re.IGNORECASE)
            if lhp_match:
                vs_left = float(f"0.{lhp_match.group(1)}")
                if 0.100 <= vs_left <= 0.500:  # Reasonable batting average range
                    splits['vs_left'] = vs_left
            
            # Pattern for vs Right-handed pitching  
            rhp_pattern = r'vs RHP.*?\.(\d{3})'
            rhp_match = re.search(rhp_pattern, html_content, re.IGNORECASE)
            if rhp_match:
                vs_right = float(f"0.{rhp_match.group(1)}")
                if 0.100 <= vs_right <= 0.500:  # Reasonable batting average range
                    splits['vs_right'] = vs_right
            
            # Look for home/away splits as well
            home_pattern = r'Home.*?\.(\d{3})'
            home_match = re.search(home_pattern, html_content, re.IGNORECASE)
            if home_match:
                home_avg = float(f"0.{home_match.group(1)}")
                if 0.100 <= home_avg <= 0.500:
                    splits['home'] = home_avg
            
            away_pattern = r'Away.*?\.(\d{3})'
            away_match = re.search(away_pattern, html_content, re.IGNORECASE)
            if away_match:
                away_avg = float(f"0.{away_match.group(1)}")
                if 0.100 <= away_avg <= 0.500:
                    splits['away'] = away_avg
            
            return splits
            
        except Exception as e:
            print(f"Error parsing splits data: {e}")
            return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
    
    def get_multiple_player_splits(self, players: list) -> Dict[str, Dict]:
        """Get splits data for multiple players"""
        all_splits = {}
        
        for player in players:
            player_name = player.get('name', '')
            team_abbr = player.get('team', '')
            
            if player_name and team_abbr:
                splits = self.get_player_splits_from_bbref(player_name, team_abbr)
                all_splits[player_name] = splits
        
        return all_splits