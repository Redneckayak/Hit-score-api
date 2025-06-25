import json
import os
import time
from datetime import datetime, timedelta, date
from typing import Dict, Optional
import pandas as pd
from data_fetcher import MLBDataFetcher
from ranking_calculator import RankingCalculator


class DataCache:
    """Manages cached MLB data with scheduled refreshes"""
    
    def __init__(self, cache_duration_minutes: int = 60):
        self.cache_duration = cache_duration_minutes * 60  # Convert to seconds
        self.cache_file = 'data/rankings_cache.json'
        self.last_update_file = 'data/last_update.json'
        self.data_fetcher = MLBDataFetcher()
        self.ranking_calculator = RankingCalculator()
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
    
    def _get_last_update_time(self) -> Optional[datetime]:
        """Get the timestamp of the last data update"""
        try:
            if os.path.exists(self.last_update_file):
                with open(self.last_update_file, 'r') as f:
                    data = json.load(f)
                    return datetime.fromisoformat(data['last_update'])
        except Exception as e:
            print(f"Error reading last update time: {e}")
        return None
    
    def _set_last_update_time(self):
        """Set the timestamp of the last data update"""
        try:
            with open(self.last_update_file, 'w') as f:
                json.dump({
                    'last_update': datetime.now().isoformat(),
                    'cache_duration_minutes': self.cache_duration // 60
                }, f)
        except Exception as e:
            print(f"Error setting last update time: {e}")
    
    def _is_cache_expired(self) -> bool:
        """Check if the cache has expired (daily at 3 AM CST or hourly updates)"""
        last_update = self._get_last_update_time()
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
        
        # Check for daily refresh at 3 AM CST
        today_3am_cst = current_time.replace(hour=3, minute=0, second=0, microsecond=0)
        if current_time.date() > last_update.date() and current_time >= today_3am_cst:
            return True
        
        # Fallback to hourly updates with grace period
        next_hour = last_update.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        grace_period = next_hour + timedelta(minutes=10)
        
        return current_time >= grace_period
    
    def _fetch_fresh_data(self) -> Optional[pd.DataFrame]:
        """Fetch fresh data from MLB API with robust error handling"""
        try:
            print("Fetching fresh MLB data...")
            
            # Attempt to get data with retry logic
            max_attempts = 2
            for attempt in range(max_attempts):
                try:
                    # Get today's games and pitcher matchups
                    games = self.data_fetcher.get_todays_games()
                    pitcher_matchups = self.data_fetcher.get_pitcher_matchups(games)
                    
                    # Get hitter stats
                    hitter_stats = self.data_fetcher.get_hitter_recent_stats()
                    
                    if hitter_stats.empty:
                        if attempt < max_attempts - 1:
                            print(f"No hitter stats on attempt {attempt + 1}, retrying...")
                            continue
                        else:
                            print("No hitter stats available after retries")
                            # Return cached data if fresh fetch fails
                            cached_data = self._load_from_cache()
                            if cached_data is not None:
                                print("Using cached 2025 data due to API unavailability")
                                return cached_data
                            return None
                    
                    # Calculate rankings
                    rankings_df = self.ranking_calculator.calculate_rankings(hitter_stats, pitcher_matchups)
                    
                    if not rankings_df.empty:
                        # Create backup before any data operations
                        from data_backup import DataBackupManager
                        backup_manager = DataBackupManager()
                        backup_manager.create_daily_backup()
                        
                        # Auto-record predictions for elite players
                        self._auto_record_predictions(rankings_df)
                        
                        # Verify data integrity
                        integrity_report = backup_manager.verify_data_integrity()
                        if not all(integrity_report.values()):
                            print(f"Data integrity warning: {integrity_report}")
                        
                        # Save to cache
                        self._save_to_cache(rankings_df)
                        self._set_last_update_time()
                        print(f"Successfully cached {len(rankings_df)} player rankings with 2025 data")
                        return rankings_df
                    else:
                        if attempt < max_attempts - 1:
                            print(f"Empty rankings on attempt {attempt + 1}, retrying...")
                            continue
                            
                except Exception as fetch_error:
                    if attempt < max_attempts - 1:
                        print(f"Fetch attempt {attempt + 1} failed: {fetch_error}, retrying...")
                        continue
                    else:
                        raise fetch_error
            
            # If all attempts failed, use cached data
            cached_data = self._load_from_cache()
            if cached_data is not None:
                print("All fetch attempts failed, using cached 2025 data")
                return cached_data
            
            return None
            
        except Exception as e:
            print(f"Error fetching fresh data: {e}")
            return None
    
    def _auto_record_predictions(self, rankings_df: pd.DataFrame, min_score: float = 2.5):
        """Automatically record daily predictions for elite players"""
        try:
            today = date.today().isoformat()
            
            # Check if predictions already recorded for today
            predictions_file = 'data/prediction_history.json'
            try:
                with open(predictions_file, 'r') as f:
                    predictions_data = json.load(f)
                if today in predictions_data:
                    return  # Already recorded today
            except (FileNotFoundError, json.JSONDecodeError):
                predictions_data = {}
            
            # Filter elite players
            elite_players = rankings_df[rankings_df['hit_score'] >= min_score]
            
            if not elite_players.empty:
                daily_predictions = {}
                for _, player in elite_players.iterrows():
                    daily_predictions[str(player['player_id'])] = {
                        'player_name': player['player_name'],
                        'team': player['team'],
                        'position': player['position'],
                        'hit_score': float(player['hit_score']),
                        'batting_avg': float(player.get('batting_avg', 0.238)),
                        'opposing_pitcher': player.get('opposing_pitcher', 'Unknown'),
                        'pitcher_hand': player.get('pitcher_hand', 'Unknown'),
                        'predicted_date': today,
                        'actual_hits': None,
                        'actual_at_bats': None,
                        'got_hit': None
                    }
                
                predictions_data[today] = daily_predictions
                
                with open(predictions_file, 'w') as f:
                    json.dump(predictions_data, f, indent=2)
                
                print(f"Auto-recorded {len(daily_predictions)} predictions for {today}")
                
        except Exception as e:
            print(f"Error auto-recording predictions: {e}")

    def _save_to_cache(self, rankings_df: pd.DataFrame):
        """Save rankings data to cache file"""
        try:
            # Convert DataFrame to JSON-serializable format
            cache_data = {
                'rankings': rankings_df.to_dict('records'),
                'columns': list(rankings_df.columns),
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, default=str)
            
            # Auto-record predictions for elite players
            self._auto_record_predictions(rankings_df)
                
        except Exception as e:
            print(f"Error saving to cache: {e}")
    
    def _load_from_cache(self) -> Optional[pd.DataFrame]:
        """Load rankings data from cache file"""
        try:
            if not os.path.exists(self.cache_file):
                return None
                
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Convert back to DataFrame
            rankings_df = pd.DataFrame(cache_data['rankings'])
            
            if not rankings_df.empty:
                print(f"Loaded {len(rankings_df)} cached rankings")
                return rankings_df
                
        except Exception as e:
            print(f"Error loading from cache: {e}")
        
        return None
    
    def get_rankings(self, force_refresh: bool = False) -> pd.DataFrame:
        """Get rankings data (cached or fresh)"""
        
        # Check if we need to refresh
        if force_refresh or self._is_cache_expired():
            fresh_data = self._fetch_fresh_data()
            if fresh_data is not None:
                return fresh_data
            else:
                print("Failed to fetch fresh data, trying cache...")
        
        # Try to load from cache
        cached_data = self._load_from_cache()
        if cached_data is not None:
            return cached_data
        
        # If no cache available, try one more time to fetch fresh data
        print("No cache available, attempting fresh data fetch...")
        fresh_data = self._fetch_fresh_data()
        return fresh_data if fresh_data is not None else pd.DataFrame()
    
    def get_cache_status(self) -> Dict:
        """Get information about cache status"""
        last_update = self._get_last_update_time()
        is_expired = self._is_cache_expired()
        cache_exists = os.path.exists(self.cache_file)
        
        return {
            'cache_exists': cache_exists,
            'last_update': last_update.isoformat() if last_update else None,
            'is_expired': is_expired,
            'cache_duration_minutes': self.cache_duration // 60,
            'next_update': (last_update + timedelta(seconds=self.cache_duration)).isoformat() if last_update else None
        }