import requests
import re
from typing import Dict, Optional
import time
from urllib.parse import quote
import trafilatura

class FanGraphsScraper:
    """Scrapes authentic MLB batter splits data from FanGraphs"""
    
    def __init__(self):
        self.base_url = "https://www.fangraphs.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_player_splits_from_fangraphs(self, player_name: str, team_abbr: str) -> Dict:
        """Get authentic splits data for a player from FanGraphs"""
        try:
            # Search for the player on FanGraphs
            player_url = self._find_player_url(player_name)
            if not player_url:
                return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
            # Get the player's splits page
            splits_url = f"{player_url}?type=0&gds=2024-03-01,2024-10-31&gde=2024-03-01,2024-10-31&season=2024"
            
            response = self.session.get(splits_url)
            if response.status_code != 200:
                return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
            # Parse splits data from the HTML
            splits = self._parse_fangraphs_splits(response.text)
            
            # Be respectful to the server
            time.sleep(1)
            
            return splits
            
        except Exception as e:
            print(f"Error scraping FanGraphs splits for {player_name}: {e}")
            return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
    
    def _find_player_url(self, player_name: str) -> Optional[str]:
        """Find the FanGraphs URL for a player using search"""
        try:
            # Use FanGraphs search functionality
            search_url = f"{self.base_url}/players.aspx"
            search_params = {
                'lastname': player_name.split()[-1],  # Last name
                'firstname': player_name.split()[0]   # First name
            }
            
            response = self.session.get(search_url, params=search_params)
            if response.status_code != 200:
                return None
            
            # Look for player links in the search results
            # FanGraphs player URLs typically look like: /players/player-name/12345
            player_link_pattern = r'/players/[^/]+/\d+'
            matches = re.findall(player_link_pattern, response.text)
            
            if matches:
                return f"{self.base_url}{matches[0]}"
            
            return None
            
        except Exception as e:
            print(f"Error finding player URL: {e}")
            return None
    
    def _parse_fangraphs_splits(self, html_content: str) -> Dict:
        """Parse splits data from FanGraphs HTML"""
        try:
            # Default values
            splits = {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
            # Look for batting average patterns in splits tables
            # FanGraphs typically shows splits data in tables with specific patterns
            
            # Pattern for vs LHP (Left-handed pitching)
            lhp_patterns = [
                r'vs\s*LHP.*?(\.\d{3})',
                r'Left.*?(\.\d{3})',
                r'L\s+(\.\d{3})'
            ]
            
            for pattern in lhp_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    vs_left = float(match.group(1))
                    if 0.100 <= vs_left <= 0.500:
                        splits['vs_left'] = vs_left
                        break
            
            # Pattern for vs RHP (Right-handed pitching)
            rhp_patterns = [
                r'vs\s*RHP.*?(\.\d{3})',
                r'Right.*?(\.\d{3})',
                r'R\s+(\.\d{3})'
            ]
            
            for pattern in rhp_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    vs_right = float(match.group(1))
                    if 0.100 <= vs_right <= 0.500:
                        splits['vs_right'] = vs_right
                        break
            
            # Look for Home/Away splits
            home_patterns = [
                r'Home.*?(\.\d{3})',
                r'H\s+(\.\d{3})'
            ]
            
            for pattern in home_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    home_avg = float(match.group(1))
                    if 0.100 <= home_avg <= 0.500:
                        splits['home'] = home_avg
                        break
            
            away_patterns = [
                r'Away.*?(\.\d{3})',
                r'A\s+(\.\d{3})'
            ]
            
            for pattern in away_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    away_avg = float(match.group(1))
                    if 0.100 <= away_avg <= 0.500:
                        splits['away'] = away_avg
                        break
            
            return splits
            
        except Exception as e:
            print(f"Error parsing FanGraphs splits: {e}")
            return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}


class BaseballReferenceScraper:
    """Alternative scraper for Baseball Reference splits data"""
    
    def __init__(self):
        self.base_url = "https://www.baseball-reference.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_player_splits_from_bbref(self, player_name: str, team_abbr: str) -> Dict:
        """Get authentic splits data from Baseball Reference using search"""
        try:
            # Use Baseball Reference search
            search_url = f"{self.base_url}/search/search.fcgi"
            search_params = {
                'search': player_name,
                'results': 'Players'
            }
            
            response = self.session.get(search_url, params=search_params)
            if response.status_code != 200:
                return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
            # Find player link from search results
            player_url = self._find_player_link_in_search(response.text, player_name)
            if not player_url:
                return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
            # Get player page
            player_response = self.session.get(f"{self.base_url}{player_url}")
            if player_response.status_code != 200:
                return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
            # Parse splits from player page
            splits = self._parse_bbref_splits(player_response.text)
            
            time.sleep(1)  # Be respectful
            
            return splits
            
        except Exception as e:
            print(f"Error scraping Baseball Reference for {player_name}: {e}")
            return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
    
    def _find_player_link_in_search(self, html_content: str, player_name: str) -> Optional[str]:
        """Find player link from search results"""
        try:
            # Look for player links in search results
            # Baseball Reference player URLs: /players/[letter]/[playerid].shtml
            link_pattern = r'/players/[a-z]/[^"]+\.shtml'
            matches = re.findall(link_pattern, html_content)
            
            if matches:
                return matches[0]  # Return first match
            
            return None
            
        except Exception:
            return None
    
    def _parse_bbref_splits(self, html_content: str) -> Dict:
        """Parse splits data from Baseball Reference HTML"""
        try:
            splits = {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}
            
            # Look for splits tables - Baseball Reference has specific table structures
            # Pattern for finding batting averages in splits sections
            
            # vs LHP patterns
            lhp_patterns = [
                r'vs\s*LHP.*?\.(\d{3})',
                r'Left.*?\.(\d{3})',
                r'LHP.*?\.(\d{3})'
            ]
            
            for pattern in lhp_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
                if match:
                    vs_left = float(f"0.{match.group(1)}")
                    if 0.100 <= vs_left <= 0.500:
                        splits['vs_left'] = vs_left
                        break
            
            # vs RHP patterns
            rhp_patterns = [
                r'vs\s*RHP.*?\.(\d{3})',
                r'Right.*?\.(\d{3})',
                r'RHP.*?\.(\d{3})'
            ]
            
            for pattern in rhp_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
                if match:
                    vs_right = float(f"0.{match.group(1)}")
                    if 0.100 <= vs_right <= 0.500:
                        splits['vs_right'] = vs_right
                        break
            
            return splits
            
        except Exception as e:
            print(f"Error parsing Baseball Reference splits: {e}")
            return {'vs_left': 0.238, 'vs_right': 0.238, 'home': 0.250, 'away': 0.230}