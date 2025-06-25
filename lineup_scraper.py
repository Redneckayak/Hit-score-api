import requests
import trafilatura
import re
import json
from typing import Dict, List, Set
from datetime import datetime


class MLBLineupScraper:
    """Scrapes starting lineups from MLB.com API endpoints"""
    
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_todays_starting_lineups(self) -> Dict[str, List[str]]:
        """Get today's starting lineups from ESPN API"""
        try:
            print("Fetching starting lineups from ESPN...")
            
            # Get today's date
            today = datetime.now().strftime('%Y%m%d')
            
            # ESPN's MLB scoreboard API
            espn_url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={today}"
            
            response = self.session.get(espn_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            lineups = {}
            
            if 'events' in data:
                for game in data['events']:
                    if 'competitions' in game:
                        for competition in game['competitions']:
                            if 'competitors' in competition:
                                for team in competition['competitors']:
                                    team_name = team.get('team', {}).get('displayName', '')
                                    team_abbr = team.get('team', {}).get('abbreviation', '')
                                    
                                    # Get roster/lineup if available
                                    if 'roster' in team:
                                        starters = []
                                        for player in team['roster']:
                                            # Check if player is in starting lineup
                                            if player.get('starter', False) or player.get('position', {}).get('abbreviation') != 'P':
                                                player_name = player.get('athlete', {}).get('displayName', '')
                                                if player_name:
                                                    starters.append(player_name)
                                        
                                        if starters:
                                            lineups[team_abbr] = starters
            
            print(f"Found lineups for {len(lineups)} teams from ESPN")
            return lineups
            
        except Exception as e:
            print(f"Error fetching lineups from ESPN: {e}")
            return {}
    
    def _parse_lineup_text(self, text_content: str) -> Dict[str, List[str]]:
        """Parse starting lineups from MLB.com text content"""
        lineups = {}
        
        try:
            lines = text_content.split('\n')
            current_team = None
            current_lineup = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for team names (usually in caps or with specific patterns)
                if self._is_team_line(line):
                    # Save previous team's lineup if exists
                    if current_team and current_lineup:
                        lineups[current_team] = current_lineup.copy()
                    
                    current_team = self._extract_team_name(line)
                    current_lineup = []
                    continue
                
                # Look for player names in batting order
                if current_team and self._is_player_line(line):
                    player_name = self._extract_player_name(line)
                    if player_name:
                        current_lineup.append(player_name)
            
            # Save the last team's lineup
            if current_team and current_lineup:
                lineups[current_team] = current_lineup.copy()
            
            return lineups
            
        except Exception as e:
            print(f"Error parsing lineup text: {e}")
            return {}
    
    def _is_team_line(self, line: str) -> bool:
        """Check if line contains a team name"""
        team_indicators = [
            'Yankees', 'Red Sox', 'Blue Jays', 'Orioles', 'Rays',
            'White Sox', 'Guardians', 'Tigers', 'Royals', 'Twins',
            'Astros', 'Angels', 'Athletics', 'Mariners', 'Rangers',
            'Braves', 'Marlins', 'Mets', 'Phillies', 'Nationals',
            'Cubs', 'Reds', 'Brewers', 'Pirates', 'Cardinals',
            'Diamondbacks', 'Rockies', 'Dodgers', 'Padres', 'Giants'
        ]
        
        return any(team in line for team in team_indicators)
    
    def _extract_team_name(self, line: str) -> str:
        """Extract team abbreviation from team line"""
        team_mapping = {
            'Yankees': 'NYY', 'Red Sox': 'BOS', 'Blue Jays': 'TOR', 
            'Orioles': 'BAL', 'Rays': 'TB', 'White Sox': 'CWS',
            'Guardians': 'CLE', 'Tigers': 'DET', 'Royals': 'KC',
            'Twins': 'MIN', 'Astros': 'HOU', 'Angels': 'LAA',
            'Athletics': 'OAK', 'Mariners': 'SEA', 'Rangers': 'TEX',
            'Braves': 'ATL', 'Marlins': 'MIA', 'Mets': 'NYM',
            'Phillies': 'PHI', 'Nationals': 'WSH', 'Cubs': 'CHC',
            'Reds': 'CIN', 'Brewers': 'MIL', 'Pirates': 'PIT',
            'Cardinals': 'STL', 'Diamondbacks': 'ARI', 'Rockies': 'COL',
            'Dodgers': 'LAD', 'Padres': 'SD', 'Giants': 'SF'
        }
        
        for team_name, abbr in team_mapping.items():
            if team_name in line:
                return abbr
        
        return line[:3].upper()  # Fallback
    
    def _is_player_line(self, line: str) -> bool:
        """Check if line contains a player name"""
        # Look for batting order numbers (1-9) or common position abbreviations
        if re.match(r'^\d+\.?\s+', line):  # Starts with number
            return True
        
        # Look for position abbreviations
        positions = ['C', 'LF', 'CF', 'RF', 'SS', 'DH', '2B', '3B', '1B']
        if any(pos in line for pos in positions):
            return True
        
        # Look for common name patterns (First Last)
        if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+', line):
            return True
        
        return False
    
    def _extract_player_name(self, line: str) -> str:
        """Extract player name from lineup line"""
        # Remove batting order number
        line = re.sub(r'^\d+\.?\s*', '', line)
        
        # Remove position abbreviations at the end
        line = re.sub(r'\s+(C|LF|CF|RF|SS|DH|2B|3B|1B)$', '', line)
        
        # Extract the name part
        name_match = re.match(r'^([A-Z][a-z]+\s+[A-Z][a-z]+)', line)
        if name_match:
            return name_match.group(1)
        
        return line.strip()
    
    def get_starter_names_set(self) -> Set[str]:
        """Get a set of all starting player names for quick lookup"""
        lineups = self.get_todays_starting_lineups()
        starter_names = set()
        
        for team, players in lineups.items():
            starter_names.update(players)
        
        return starter_names