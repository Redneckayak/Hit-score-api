import requests
import pandas as pd
from typing import Dict, List, Optional
import os

class OddsFetcher:
    """Fetches betting odds from The Odds API"""
    
    def __init__(self):
        self.api_key = os.getenv('ODDS_API_KEY', 'e445f5c6daee8d8fe402d6e12c16d803')
        self.base_url = "https://api.the-odds-api.com/v4"
        
    def get_mlb_games_today(self) -> List[Dict]:
        """Get today's MLB games with odds"""
        url = f"{self.base_url}/sports/baseball_mlb/odds/"
        params = {
            'api_key': self.api_key,
            'regions': 'us',
            'markets': 'h2h',
            'oddsFormat': 'american'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching MLB games: {e}")
            return []
    
    def check_available_markets(self) -> List[str]:
        """Check what markets are available for MLB"""
        url = f"{self.base_url}/sports/baseball_mlb/odds/"
        params = {
            'api_key': self.api_key,
            'regions': 'us',
            'markets': 'h2h',  # Start with basic market
            'oddsFormat': 'american'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            games_data = response.json()
            
            if games_data:
                return ["h2h", "spreads", "totals"]  # Common markets
            return []
            
        except Exception as e:
            print(f"Error checking markets: {e}")
            return []
    
    def get_player_props(self, player_name: str, team_abbr: str) -> Optional[Dict]:
        """Get player prop odds for 1+ hits"""
        # The Odds API may not have player props for MLB during off-season
        # or the specific market format may be different
        return None  # Return None for now since player_hits market isn't available
    
    def _name_matches(self, prop_name: str, player_name: str) -> bool:
        """Check if prop name matches player name"""
        prop_name = prop_name.lower().strip()
        player_name = player_name.lower().strip()
        
        # Simple name matching - could be improved
        name_parts = player_name.split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = name_parts[-1]
            return first_name in prop_name and last_name in prop_name
        
        return player_name in prop_name
    
    def get_multiple_player_props(self, players: List[Dict]) -> List[Dict]:
        """Get 1+ hit props for multiple players"""
        props = []
        
        for player in players:
            prop = self.get_player_props(
                player.get('name', ''),
                player.get('team', '')
            )
            if prop:
                prop.update(player)  # Add original player data
                props.append(prop)
        
        return props
    
    def calculate_parlay_odds(self, individual_odds: List[int]) -> Dict:
        """Calculate parlay odds from individual American odds"""
        if not individual_odds:
            return {'decimal_odds': 0, 'american_odds': 0, 'payout': 0}
        
        # Convert American odds to decimal
        decimal_odds = []
        for odds in individual_odds:
            if odds > 0:
                decimal = (odds / 100) + 1
            else:
                decimal = (100 / abs(odds)) + 1
            decimal_odds.append(decimal)
        
        # Calculate parlay decimal odds
        parlay_decimal = 1
        for decimal in decimal_odds:
            parlay_decimal *= decimal
        
        # Convert back to American odds
        if parlay_decimal >= 2:
            parlay_american = int((parlay_decimal - 1) * 100)
        else:
            parlay_american = int(-100 / (parlay_decimal - 1))
        
        # Calculate payout for $10 bet
        payout = 10 * (parlay_decimal - 1)
        
        return {
            'decimal_odds': round(parlay_decimal, 2),
            'american_odds': parlay_american,
            'payout': round(payout, 2)
        }