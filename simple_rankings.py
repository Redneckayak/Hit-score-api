import pandas as pd
from datetime import datetime
import requests
import json
import os
from typing import Dict, List, Optional

class SimpleMLBRankings:
    """Direct MLB data fetcher with guaranteed current 2025 season data"""
    
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MLB-Rankings/2.0',
            'Accept': 'application/json'
        })
        self.cache_file = 'data/simple_rankings_cache.json'
        self.team_lookup = {}  # Cache team ID to abbreviation mapping
        os.makedirs('data', exist_ok=True)
        self._build_team_lookup()
    
    def _build_team_lookup(self):
        """Build team ID to abbreviation lookup"""
        data = self._safe_request("teams", {'sportId': 1})
        if data and 'teams' in data:
            for team in data['teams']:
                self.team_lookup[team['id']] = team.get('abbreviation', team.get('teamCode', 'UNK'))
    
    def _safe_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make safe API request with error handling"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"API request failed: {e}")
        return None
    
    def get_todays_games(self) -> List[dict]:
        """Get today's MLB games"""
        today = datetime.now().strftime('%Y-%m-%d')
        data = self._safe_request("schedule", {'sportId': 1, 'date': today})
        
        games = []
        if data and 'dates' in data and data['dates']:
            for game_data in data['dates'][0].get('games', []):
                try:
                    away_team_id = game_data['teams']['away']['team']['id']
                    home_team_id = game_data['teams']['home']['team']['id']
                    
                    games.append({
                        'game_id': game_data['gamePk'],
                        'away_team': self.team_lookup.get(away_team_id, 'UNK'),
                        'home_team': self.team_lookup.get(home_team_id, 'UNK'),
                        'away_team_id': away_team_id,
                        'home_team_id': home_team_id
                    })
                except KeyError as e:
                    print(f"Error parsing game data: {e}")
                    continue
        return games
    
    def get_player_season_stats(self, player_id: int) -> dict:
        """Get player's 2025 season batting stats"""
        data = self._safe_request(f"people/{player_id}/stats", {
            'stats': 'season',
            'group': 'hitting',
            'season': 2025
        })
        
        if data and 'stats' in data and data['stats']:
            splits = data['stats'][0].get('splits', [])
            if splits:
                stats = splits[0].get('stat', {})
                return {
                    'batting_avg': float(stats.get('avg', 0.238)),
                    'hits': int(stats.get('hits', 0)),
                    'at_bats': int(stats.get('atBats', 0)),
                    'games': int(stats.get('gamesPlayed', 0))
                }
        
        return {'batting_avg': 0.238, 'hits': 0, 'at_bats': 0, 'games': 0}
    
    def get_player_recent_games(self, player_id: int) -> dict:
        """Get player's recent game stats"""
        data = self._safe_request(f"people/{player_id}/stats", {
            'stats': 'gameLog',
            'group': 'hitting',
            'season': 2025
        })
        
        recent_stats = {'last_5': 0, 'last_10': 0, 'last_20': 0}
        
        if data and 'stats' in data and data['stats']:
            game_logs = data['stats'][0].get('splits', [])
            
            # Sort by date (most recent first)
            game_logs.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            recent_stats['last_5'] = sum(int(game.get('stat', {}).get('hits', 0)) for game in game_logs[:5])
            recent_stats['last_10'] = sum(int(game.get('stat', {}).get('hits', 0)) for game in game_logs[:10])
            recent_stats['last_20'] = sum(int(game.get('stat', {}).get('hits', 0)) for game in game_logs[:20])
        
        return recent_stats
    
    def get_pitcher_oba(self, pitcher_id: int) -> float:
        """Get pitcher's opponent batting average"""
        data = self._safe_request(f"people/{pitcher_id}/stats", {
            'stats': 'season',
            'group': 'pitching',
            'season': 2025
        })
        
        if data and 'stats' in data and data['stats']:
            splits = data['stats'][0].get('splits', [])
            if splits:
                stats = splits[0].get('stat', {})
                return float(stats.get('avg', 0.250))  # Opponent batting average
        
        return 0.250
    
    def calculate_hit_score(self, player_data: dict) -> float:
        """Calculate hit score using the simplified formula"""
        # Player Hotness: (L5 + L10 + L20) / 26.25
        hotness = (player_data['last_5'] + player_data['last_10'] + player_data['last_20']) / 26.25
        
        # Pitcher Difficulty: Pitcher OBA / 0.238
        pitcher_factor = player_data.get('pitcher_oba', 0.250) / 0.238
        
        # Player Skill: Player BA / 0.238
        skill_factor = player_data['batting_avg'] / 0.238
        
        # Equal weighting (multiply together)
        hit_score = hotness * pitcher_factor * skill_factor
        
        return round(hit_score, 3)
    
    def get_team_roster(self, team_id: int) -> List[dict]:
        """Get active roster for a team"""
        data = self._safe_request(f"teams/{team_id}/roster", {'rosterType': 'active'})
        
        roster = []
        if data and 'roster' in data:
            for player_data in data['roster']:
                player_info = player_data['person']
                position = player_data['position']['abbreviation']
                
                # Only include position players (not pitchers)
                if position not in ['P', 'LHP', 'RHP']:
                    roster.append({
                        'player_id': player_info['id'],
                        'player_name': player_info['fullName'],
                        'position': position
                    })
        
        return roster
    
    def get_probable_pitchers(self, games: List[dict]) -> dict:
        """Get probable starting pitchers for today's games"""
        pitcher_matchups = {}
        
        for game in games:
            game_data = self._safe_request(f"schedule", {
                'gamePk': game['game_id'],
                'hydrate': 'probablePitcher'
            })
            
            if game_data and 'dates' in game_data and game_data['dates']:
                for date_data in game_data['dates']:
                    for game_info in date_data.get('games', []):
                        if game_info['gamePk'] == game['game_id']:
                            # Away team faces home pitcher
                            home_pitcher = game_info.get('teams', {}).get('home', {}).get('probablePitcher')
                            away_pitcher = game_info.get('teams', {}).get('away', {}).get('probablePitcher')
                            
                            if home_pitcher:
                                home_pitcher_oba = self.get_pitcher_oba(home_pitcher['id'])
                                pitcher_matchups[game['away_team_id']] = {
                                    'pitcher_id': home_pitcher['id'],
                                    'pitcher_name': home_pitcher['fullName'],
                                    'pitcher_oba': home_pitcher_oba
                                }
                            
                            if away_pitcher:
                                away_pitcher_oba = self.get_pitcher_oba(away_pitcher['id'])
                                pitcher_matchups[game['home_team_id']] = {
                                    'pitcher_id': away_pitcher['id'],
                                    'pitcher_name': away_pitcher['fullName'],
                                    'pitcher_oba': away_pitcher_oba
                                }
        
        return pitcher_matchups

    def generate_daily_rankings(self) -> pd.DataFrame:
        """Generate complete daily rankings with current 2025 data"""
        print("Generating fresh daily rankings...")
        
        # Get today's games
        games = self.get_todays_games()
        if not games:
            print("No games found for today")
            return pd.DataFrame()
        
        # Get pitcher matchups
        print("Fetching probable pitcher matchups...")
        pitcher_matchups = self.get_probable_pitchers(games)
        
        all_players = []
        
        for game in games:
            # Process both teams
            for team_type in ['away', 'home']:
                team_id = game[f'{team_type}_team_id']
                team_abbr = game[f'{team_type}_team']
                
                # Get pitcher matchup for this team
                matchup_info = pitcher_matchups.get(team_id, {
                    'pitcher_oba': 0.250,
                    'pitcher_name': 'TBD'
                })
                
                # Get roster
                roster = self.get_team_roster(team_id)
                
                for player in roster:
                    try:
                        # Get season stats
                        season_stats = self.get_player_season_stats(player['player_id'])
                        
                        # Get recent games
                        recent_stats = self.get_player_recent_games(player['player_id'])
                        
                        # Only include players with games played
                        if season_stats['games'] > 0:
                            player_data = {
                                'player_id': player['player_id'],
                                'player_name': player['player_name'],
                                'team': team_abbr,
                                'position': player['position'],
                                'batting_avg': season_stats['batting_avg'],
                                'last_5': recent_stats['last_5'],
                                'last_10': recent_stats['last_10'],
                                'last_20': recent_stats['last_20'],
                                'games_played': season_stats['games'],
                                'pitcher_oba': matchup_info['pitcher_oba'],
                                'opposing_pitcher': matchup_info['pitcher_name'],
                                'is_home': team_type == 'home'
                            }
                            
                            # Calculate hit score with actual pitcher OBA
                            player_data['hit_score'] = self.calculate_hit_score(player_data)
                            
                            all_players.append(player_data)
                            
                            print(f"Player {player['player_id']}: {player['player_name']} - BA: {season_stats['batting_avg']:.3f}")
                    
                    except Exception as e:
                        print(f"Error processing player {player['player_name']}: {e}")
                        continue
        
        if not all_players:
            print("No player data collected")
            return pd.DataFrame()
        
        # Create DataFrame and sort by hit score
        df = pd.DataFrame(all_players)
        df = df.sort_values('hit_score', ascending=False).reset_index(drop=True)
        
        # Filter out inactive players using lineup/injury data
        from data_fetcher import MLBDataFetcher
        fetcher = MLBDataFetcher()
        df = fetcher.filter_active_players(df)
        
        # Re-sort after filtering
        df = df.sort_values('hit_score', ascending=False).reset_index(drop=True)
        
        # Create backup and verify integrity
        from data_backup import DataBackupManager
        backup_manager = DataBackupManager()
        backup_manager.create_daily_backup()
        
        # Auto-record predictions for elite players
        self._auto_record_predictions(df)
        
        # Verify recording worked
        if not backup_manager.auto_record_verification():
            print("WARNING: Auto-recording may have failed")
        
        # Save to cache
        cache_data = {
            'rankings': df.to_dict('records'),
            'generated_at': datetime.now().isoformat(),
            'total_players': len(df)
        }
        
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"Cached rankings for {len(df)} players")
        except Exception as e:
            print(f"Error saving cache: {e}")
        
        return df
    
    def load_cached_rankings(self) -> Optional[pd.DataFrame]:
        """Load rankings from cache"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    
                df = pd.DataFrame(cache_data['rankings'])
                print(f"Loaded {len(df)} cached rankings from {cache_data['generated_at']}")
                return df
        except Exception as e:
            print(f"Error loading cache: {e}")
        
        return None
    
    def _is_cache_expired(self) -> bool:
        """Check if cache is expired (daily at 3 AM CST)"""
        try:
            if not os.path.exists(self.cache_file):
                return True
                
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            if 'generated_at' not in cache_data:
                return True
                
            from datetime import datetime
            import pytz
            
            # Parse cache timestamp
            cache_time = datetime.fromisoformat(cache_data['generated_at'].replace('Z', '+00:00'))
            
            # Convert to CST
            cst = pytz.timezone('America/Chicago')
            current_time = datetime.now(cst)
            
            # Make cache_time timezone-aware if it isn't already
            if cache_time.tzinfo is None:
                cache_time = cst.localize(cache_time)
            else:
                cache_time = cache_time.astimezone(cst)
            
            # Check for daily refresh at 3 AM CST
            today_3am_cst = current_time.replace(hour=3, minute=0, second=0, microsecond=0)
            if current_time.date() > cache_time.date() and current_time >= today_3am_cst:
                return True
                
            return False
        except Exception as e:
            print(f"Error checking cache expiration: {e}")
            return True
    
    def _auto_record_predictions(self, rankings_df: pd.DataFrame, min_score: float = 2.5):
        """Automatically record daily predictions for elite players"""
        try:
            from datetime import date
            import json
            
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
                        'got_hit': None,
                        'rank': len([p for p in daily_predictions]) + 1
                    }
                
                predictions_data[today] = daily_predictions
                
                with open(predictions_file, 'w') as f:
                    json.dump(predictions_data, f, indent=2)
                
                print(f"Auto-recorded {len(daily_predictions)} predictions for {today}")
                
                # Also record top 3 picks
                self._record_top_3_picks(daily_predictions, today)
                
        except Exception as e:
            print(f"Error auto-recording predictions: {e}")
    
    def _record_top_3_picks(self, daily_predictions: dict, today: str):
        """Record top 3 daily picks"""
        try:
            import json
            
            # Load existing top 3 picks
            top_3_file = 'data/top_3_picks_history.json'
            try:
                with open(top_3_file, 'r') as f:
                    top_3_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                top_3_data = {}
            
            if today not in top_3_data:
                # Get top 3 players by hit score
                sorted_predictions = sorted(daily_predictions.items(), key=lambda x: x[1]['hit_score'], reverse=True)
                top_3_picks = {}
                
                for i, (player_id, pred) in enumerate(sorted_predictions[:3]):
                    top_3_picks[player_id] = pred.copy()
                    top_3_picks[player_id]['rank'] = i + 1
                
                top_3_data[today] = top_3_picks
                
                with open(top_3_file, 'w') as f:
                    json.dump(top_3_data, f, indent=2)
                
        except Exception as e:
            print(f"Error recording top 3 picks: {e}")
    
    def get_rankings(self, force_refresh: bool = False) -> pd.DataFrame:
        """Get rankings (cached or fresh)"""
        if not force_refresh:
            cached_df = self.load_cached_rankings()
            if cached_df is not None and not cached_df.empty:
                # Check if cached data has pitcher information
                if 'opposing_pitcher' in cached_df.columns and 'pitcher_oba' in cached_df.columns:
                    # Check if cache is expired (daily at 3 AM CST)
                    if self._is_cache_expired():
                        print("Cache expired, generating fresh rankings...")
                        return self.generate_daily_rankings()
                    return cached_df
                else:
                    print("Cached data missing pitcher info, generating fresh rankings...")
        
        # Generate fresh rankings with complete pitcher matchup data
        return self.generate_daily_rankings()
