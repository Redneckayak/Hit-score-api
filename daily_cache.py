import json
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from data_fetcher import MLBDataFetcher
from ranking_calculator import RankingCalculator

class DailyCacheManager:
    """Manages daily caching of stable MLB data (batting averages, season stats) 
    and hourly updates of dynamic data (lineups, matchups)"""
    
    def __init__(self):
        self.data_fetcher = MLBDataFetcher()
        self.ranking_calculator = RankingCalculator()
        self.daily_cache_file = 'data/daily_player_cache.json'
        self.matchup_cache_file = 'data/hourly_matchup_cache.json'
        self.last_daily_update_file = 'data/last_daily_update.json'
        self.last_matchup_update_file = 'data/last_matchup_update.json'
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
    
    def _get_last_daily_update(self) -> Optional[datetime]:
        """Get timestamp of last daily data update"""
        try:
            if os.path.exists(self.last_daily_update_file):
                with open(self.last_daily_update_file, 'r') as f:
                    data = json.load(f)
                    return datetime.fromisoformat(data['last_update'])
        except Exception as e:
            print(f"Error reading daily update time: {e}")
        return None
    
    def _set_last_daily_update(self):
        """Set timestamp of last daily data update"""
        try:
            with open(self.last_daily_update_file, 'w') as f:
                json.dump({
                    'last_update': datetime.now().isoformat()
                }, f)
        except Exception as e:
            print(f"Error setting daily update time: {e}")
    
    def _is_daily_cache_expired(self) -> bool:
        """Check if daily cache needs refresh (once per day at 3 AM CST)"""
        last_update = self._get_last_daily_update()
        if not last_update:
            return True
        
        # Convert to CST (UTC-6)
        import pytz
        cst = pytz.timezone('America/Chicago')
        current_time = datetime.now(cst)
        
        # Make last_update timezone-aware if it isn't already
        if last_update.tzinfo is None:
            last_update = cst.localize(last_update)
        else:
            last_update = last_update.astimezone(cst)
        
        # Check if it's past 3 AM CST today and we haven't updated today
        today_3am_cst = current_time.replace(hour=3, minute=0, second=0, microsecond=0)
        if current_time.date() > last_update.date():
            # New day - need update if past 3 AM CST
            return current_time >= today_3am_cst
        
        return False
    
    def _fetch_daily_player_data(self) -> Optional[Dict]:
        """Fetch stable daily data: batting averages, season stats, player info"""
        try:
            print("Fetching daily player data (batting averages, season stats)...")
            
            # Get all active players with season stats
            hitter_stats = self.data_fetcher.get_hitter_recent_stats()
            
            if hitter_stats.empty:
                print("No player stats available")
                return None
            
            # Convert to dict format for caching
            daily_data = {
                'player_stats': hitter_stats.to_dict('records'),
                'update_timestamp': datetime.now().isoformat(),
                'total_players': len(hitter_stats)
            }
            
            print(f"Cached daily data for {len(hitter_stats)} players")
            return daily_data
            
        except Exception as e:
            print(f"Error fetching daily player data: {e}")
            return None
    
    def _save_daily_cache(self, daily_data: Dict):
        """Save daily player data to cache"""
        try:
            with open(self.daily_cache_file, 'w') as f:
                json.dump(daily_data, f, indent=2)
            self._set_last_daily_update()
        except Exception as e:
            print(f"Error saving daily cache: {e}")
    
    def _load_daily_cache(self) -> Optional[Dict]:
        """Load daily player data from cache"""
        try:
            if os.path.exists(self.daily_cache_file):
                with open(self.daily_cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading daily cache: {e}")
        return None
    
    def get_daily_player_data(self, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """Get daily player data (cached or fresh)"""
        if not force_refresh and not self._is_daily_cache_expired():
            # Use cached data
            cached_data = self._load_daily_cache()
            if cached_data:
                print(f"Using cached daily data for {cached_data['total_players']} players")
                return pd.DataFrame(cached_data['player_stats'])
        
        # Fetch fresh daily data
        daily_data = self._fetch_daily_player_data()
        if daily_data:
            self._save_daily_cache(daily_data)
            return pd.DataFrame(daily_data['player_stats'])
        
        # Fallback to cached data if fresh fetch fails
        cached_data = self._load_daily_cache()
        if cached_data:
            print("Fresh fetch failed, using cached daily data")
            return pd.DataFrame(cached_data['player_stats'])
        
        return None
    
    def _get_last_matchup_update(self) -> Optional[datetime]:
        """Get timestamp of last matchup update"""
        try:
            if os.path.exists(self.last_matchup_update_file):
                with open(self.last_matchup_update_file, 'r') as f:
                    data = json.load(f)
                    return datetime.fromisoformat(data['last_update'])
        except Exception as e:
            print(f"Error reading matchup update time: {e}")
        return None
    
    def _is_matchup_cache_expired(self) -> bool:
        """Check if matchup cache needs refresh (hourly)"""
        last_update = self._get_last_matchup_update()
        if not last_update:
            return True
        
        current_time = datetime.now()
        next_hour = last_update.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        return current_time >= next_hour
    
    def _fetch_matchup_data(self) -> Optional[Dict]:
        """Fetch dynamic data: today's games, lineups, pitcher matchups"""
        try:
            print("Fetching today's matchups and lineups...")
            
            # Get today's games
            games = self.data_fetcher.get_todays_games()
            
            # Get pitcher matchups
            pitcher_matchups = self.data_fetcher.get_pitcher_matchups(games)
            
            # Get starting lineups
            starting_lineups = self.data_fetcher.get_todays_starting_lineups()
            
            matchup_data = {
                'games': games,
                'pitcher_matchups': pitcher_matchups,
                'starting_lineups': starting_lineups,
                'update_timestamp': datetime.now().isoformat()
            }
            
            print(f"Cached matchup data for {len(games)} games")
            return matchup_data
            
        except Exception as e:
            print(f"Error fetching matchup data: {e}")
            return None
    
    def _save_matchup_cache(self, matchup_data: Dict):
        """Save matchup data to cache"""
        try:
            with open(self.matchup_cache_file, 'w') as f:
                json.dump(matchup_data, f, indent=2)
            
            with open(self.last_matchup_update_file, 'w') as f:
                json.dump({
                    'last_update': datetime.now().isoformat()
                }, f)
        except Exception as e:
            print(f"Error saving matchup cache: {e}")
    
    def _load_matchup_cache(self) -> Optional[Dict]:
        """Load matchup data from cache"""
        try:
            if os.path.exists(self.matchup_cache_file):
                with open(self.matchup_cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading matchup cache: {e}")
        return None
    
    def get_matchup_data(self, force_refresh: bool = False) -> Optional[Dict]:
        """Get matchup data (cached or fresh)"""
        if not force_refresh and not self._is_matchup_cache_expired():
            # Use cached data
            cached_data = self._load_matchup_cache()
            if cached_data:
                print("Using cached matchup data")
                return cached_data
        
        # Fetch fresh matchup data
        matchup_data = self._fetch_matchup_data()
        if matchup_data:
            self._save_matchup_cache(matchup_data)
            return matchup_data
        
        # Fallback to cached data if fresh fetch fails
        cached_data = self._load_matchup_cache()
        if cached_data:
            print("Fresh matchup fetch failed, using cached data")
            return cached_data
        
        return None
    
    def get_complete_rankings(self, force_refresh_daily: bool = False, force_refresh_matchups: bool = False) -> Optional[pd.DataFrame]:
        """Get complete rankings combining daily player data with current matchups"""
        try:
            # Get daily player data (batting averages, season stats)
            player_data = self.get_daily_player_data(force_refresh_daily)
            if player_data is None or player_data.empty:
                print("No player data available")
                return None
            
            # Get matchup data (games, lineups, pitchers)
            matchup_data = self.get_matchup_data(force_refresh_matchups)
            if matchup_data is None:
                print("No matchup data available")
                return None
            
            # Calculate rankings combining both datasets
            rankings_df = self.ranking_calculator.calculate_rankings(
                player_data, 
                matchup_data.get('pitcher_matchups', {})
            )
            
            if rankings_df is None or rankings_df.empty:
                print("Rankings calculation failed or returned empty data")
                return None
            
            # Filter to only starting players if lineups available
            if matchup_data.get('starting_lineups'):
                filtered_df = self.data_fetcher.filter_active_players(rankings_df)
                if not filtered_df.empty:
                    rankings_df = filtered_df
            
            print(f"Generated rankings for {len(rankings_df)} players")
            return rankings_df
            
        except Exception as e:
            print(f"Error generating complete rankings: {e}")
            return None
    
    def get_cache_status(self) -> Dict:
        """Get status of both caches"""
        daily_update = self._get_last_daily_update()
        matchup_update = self._get_last_matchup_update()
        
        return {
            'daily_cache': {
                'last_update': daily_update.isoformat() if daily_update else None,
                'expired': self._is_daily_cache_expired(),
                'next_update': '6:00 AM ET daily'
            },
            'matchup_cache': {
                'last_update': matchup_update.isoformat() if matchup_update else None,
                'expired': self._is_matchup_cache_expired(),
                'next_update': 'Top of every hour'
            }
        }