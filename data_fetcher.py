import requests
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional
import time
from mlb_statscast_fetcher import MLBOfficialAPIFetcher

class MLBDataFetcher:
    """Fetches MLB data from the Stats API"""
    
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1"
        self.official_api_fetcher = MLBOfficialAPIFetcher()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MLB-Hitter-Rankings/1.0'
        })
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make a request to the MLB Stats API with enhanced error handling"""
        import time
        
        try:
            url = f"{self.base_url}{endpoint}"
            
            # Add retry logic for better stability
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.session.get(url, params=params, timeout=15)
                    
                    # Handle specific HTTP status codes
                    if response.status_code == 404:
                        # Don't retry 404s - data doesn't exist
                        print(f"Data not found for {endpoint}")
                        return None
                    elif response.status_code == 429:
                        # Rate limited - wait longer
                        if attempt < max_retries - 1:
                            wait_time = (2 ** attempt) * 5  # Exponential backoff
                            print(f"Rate limited, waiting {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                    
                    response.raise_for_status()
                    return response.json()
                    
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"Connection issue (attempt {attempt + 1}), retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        print(f"Connection failed after {max_retries} attempts: {e}")
                        return None
                        
        except requests.exceptions.RequestException as e:
            print(f"Request error for {endpoint}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return None
            
        return None
    
    def get_todays_games(self) -> List[Dict]:
        """Get today's MLB games"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        data = self._make_request(f"/schedule", {
            'sportId': 1,  # MLB
            'date': today,
            'hydrate': 'team,linescore,probablePitcher'
        })
        
        if not data or 'dates' not in data or not data['dates']:
            return []
        
        games = []
        for date_info in data['dates']:
            for game in date_info.get('games', []):
                if game.get('status', {}).get('statusCode') in ['S', 'P', 'I']:  # Scheduled, Pre-game, In progress
                    game_info = {
                        'game_id': game['gamePk'],
                        'away_team': game['teams']['away']['team']['abbreviation'],
                        'home_team': game['teams']['home']['team']['abbreviation'],
                        'away_team_id': game['teams']['away']['team']['id'],
                        'home_team_id': game['teams']['home']['team']['id'],
                        'game_time': game.get('gameDate'),
                        'status': game['status']['detailedState']
                    }
                    
                    # Add probable pitchers if available
                    if 'probablePitcher' in game['teams']['away']:
                        game_info['away_pitcher'] = {
                            'id': game['teams']['away']['probablePitcher']['id'],
                            'name': game['teams']['away']['probablePitcher']['fullName']
                        }
                    
                    if 'probablePitcher' in game['teams']['home']:
                        game_info['home_pitcher'] = {
                            'id': game['teams']['home']['probablePitcher']['id'],
                            'name': game['teams']['home']['probablePitcher']['fullName']
                        }
                    
                    games.append(game_info)
        
        return games
    
    def get_team_roster(self, team_id: int) -> List[Dict]:
        """Get active roster for a team"""
        data = self._make_request(f"/teams/{team_id}/roster", {
            'rosterType': 'active'
        })
        
        if not data or 'roster' not in data:
            return []
        
        players = []
        for player_info in data['roster']:
            player = player_info['person']
            position = player_info['position']
            
            # Only include position players (not pitchers)
            if position['abbreviation'] not in ['P']:
                players.append({
                    'player_id': player['id'],
                    'player_name': player['fullName'],
                    'position': position['abbreviation'],
                    'team_id': team_id
                })
        
        return players
    
    def get_team_batting_order(self, team_id: int, game_id: int = None) -> Dict[int, int]:
        """Get batting order for a team from recent lineups"""
        # Try to get today's lineup first
        if game_id:
            lineup_data = self._make_request(f"/game/{game_id}/boxscore")
            if lineup_data and 'teams' in lineup_data:
                for team_key in ['home', 'away']:
                    team_data = lineup_data['teams'][team_key]
                    if team_data.get('team', {}).get('id') == team_id:
                        batting_order = {}
                        batters = team_data.get('batters', [])
                        for i, player_id in enumerate(batters[:9]):  # First 9 are starting lineup
                            batting_order[player_id] = i + 1
                        return batting_order
        
        # Fallback: get recent game lineups
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        for date_str in [today, yesterday]:
            schedule_data = self._make_request(f"/schedule", {
                'sportId': 1,
                'teamId': team_id,
                'date': date_str,
                'hydrate': 'lineups'
            })
            
            if schedule_data and 'dates' in schedule_data:
                for date_info in schedule_data['dates']:
                    for game in date_info.get('games', []):
                        if 'lineups' in game and game['lineups']:
                            # Check both home and away lineups
                            for team_key in ['home', 'away']:
                                if game['teams'][team_key]['team']['id'] == team_id:
                                    lineup = game['lineups'].get(team_key)
                                    if lineup:
                                        batting_order = {}
                                        for player in lineup:
                                            if 'battingOrder' in player:
                                                player_id = player['person']['id']
                                                order = int(player['battingOrder']) // 100  # Convert 100, 200, etc. to 1, 2, etc.
                                                batting_order[player_id] = order
                                        return batting_order
        
        return {}
    
    def get_player_recent_stats(self, player_id: int, days_back: int = 20) -> Dict:
        """Get recent hitting stats for a player"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        data = self._make_request(f"/people/{player_id}/stats", {
            'stats': 'gameLog',
            'group': 'hitting',
            'season': 2025,
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d')
        })
        
        if not data or 'stats' not in data or not data['stats']:
            return {'hits_last_5': 0, 'hits_last_10': 0, 'hits_last_20': 0, 'games_played': 0}
        
        game_logs = data['stats'][0].get('splits', [])
        
        # Sort by date (most recent first)
        game_logs.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        hits_5 = sum(int(game.get('stat', {}).get('hits', 0)) for game in game_logs[:5])
        hits_10 = sum(int(game.get('stat', {}).get('hits', 0)) for game in game_logs[:10])
        hits_20 = sum(int(game.get('stat', {}).get('hits', 0)) for game in game_logs[:20])
        
        return {
            'hits_last_5': hits_5,
            'hits_last_10': hits_10,
            'hits_last_20': hits_20,
            'games_played': len(game_logs)
        }
    
    def get_pitcher_oba(self, pitcher_id: int) -> float:
        """Get pitcher's opponent batting average for current season"""
        data = self._make_request(f"/people/{pitcher_id}/stats", {
            'stats': 'season',
            'group': 'pitching',
            'season': 2025
        })
        
        if not data or 'stats' not in data or not data['stats']:
            return 0.250  # Default OBA if no data
        
        pitching_stats = data['stats'][0].get('splits', [])
        
        if not pitching_stats:
            return 0.250
        
        stats = pitching_stats[0].get('stat', {})
        oba = float(stats.get('avg', '0.250'))  # 'avg' is opponent batting average
        
        return oba
    
    def get_hitter_recent_stats(self) -> pd.DataFrame:
        """Get recent stats for all active hitters"""
        # Get all teams
        teams_data = self._make_request("/teams", {'sportId': 1})
        
        if not teams_data or 'teams' not in teams_data:
            return pd.DataFrame()
        
        all_hitters = []
        
        for team in teams_data['teams']:
            if team.get('sport', {}).get('id') == 1:  # MLB only
                team_id = team['id']
                team_abbr = team['abbreviation']
                
                # Get roster
                roster = self.get_team_roster(team_id)
                
                for player in roster:
                    # Get recent stats
                    recent_stats = self.get_player_recent_stats(player['player_id'])
                    
                    # Only include players who have played recently
                    if recent_stats['games_played'] > 0:
                        hitter_data = {
                            'player_id': player['player_id'],
                            'player_name': player['player_name'],
                            'team': team_abbr,
                            'team_id': team_id,
                            'position': player['position'],
                            **recent_stats
                        }
                        all_hitters.append(hitter_data)
                
                # Add small delay to avoid overwhelming the API
                time.sleep(0.1)
        
        return pd.DataFrame(all_hitters)
    
    def get_pitcher_matchups(self, games: List[Dict]) -> Dict[int, Dict]:
        """Get pitcher matchups for today's games"""
        pitcher_matchups = {}
        
        for game in games:
            # Away team hitters face home pitcher
            if 'home_pitcher' in game:
                home_pitcher_oba = self.get_pitcher_oba(game['home_pitcher']['id'])
                home_pitcher_hand = self.get_pitcher_handedness(game['home_pitcher']['id'])
                away_team_offense = self.get_team_recent_offense(game['away_team_id'])
                
                pitcher_matchups[game['away_team_id']] = {
                    'opposing_pitcher': game['home_pitcher']['name'],
                    'opposing_pitcher_id': game['home_pitcher']['id'],
                    'pitcher_oba': home_pitcher_oba,
                    'pitcher_hand': home_pitcher_hand,
                    'opponent_team': game['home_team'],
                    'team_offense': away_team_offense,
                    'is_home': False
                }
            
            # Home team hitters face away pitcher
            if 'away_pitcher' in game:
                away_pitcher_oba = self.get_pitcher_oba(game['away_pitcher']['id'])
                away_pitcher_hand = self.get_pitcher_handedness(game['away_pitcher']['id'])
                home_team_offense = self.get_team_recent_offense(game['home_team_id'])
                
                pitcher_matchups[game['home_team_id']] = {
                    'opposing_pitcher': game['away_pitcher']['name'],
                    'opposing_pitcher_id': game['away_pitcher']['id'],
                    'pitcher_oba': away_pitcher_oba,
                    'pitcher_hand': away_pitcher_hand,
                    'opponent_team': game['away_team'],
                    'team_offense': home_team_offense,
                    'is_home': True
                }
            
            # Add delay between requests
            time.sleep(0.1)
        
        return pitcher_matchups
    
    def get_live_game_stats(self, player_id: int) -> Dict:
        """Get live stats for a player from today's games"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get today's game logs for the player
        data = self._make_request(f"/people/{player_id}/stats", {
            'stats': 'gameLog',
            'group': 'hitting',
            'season': 2025,
            'startDate': today,
            'endDate': today
        })
        
        if not data or 'stats' not in data or not data['stats']:
            return {'hits_today': 0, 'at_bats_today': 0, 'game_status': 'Not Started'}
        
        game_logs = data['stats'][0].get('splits', [])
        
        if not game_logs:
            return {'hits_today': 0, 'at_bats_today': 0, 'game_status': 'Not Started'}
        
        # Get today's stats (should be only one game)
        today_stats = game_logs[0].get('stat', {})
        
        return {
            'hits_today': int(today_stats.get('hits', 0)),
            'at_bats_today': int(today_stats.get('atBats', 0)),
            'game_status': 'In Progress' if int(today_stats.get('atBats', 0)) > 0 else 'Not Started'
        }
    
    def get_todays_live_results(self, player_ids: List[int]) -> Dict[int, Dict]:
        """Get live results for multiple players"""
        live_results = {}
        
        for player_id in player_ids:
            live_results[player_id] = self.get_live_game_stats(player_id)
            # Small delay to avoid overwhelming the API
            time.sleep(0.1)
        
        return live_results
    
    def get_pitcher_handedness(self, pitcher_id: int) -> str:
        """Get pitcher's throwing hand (L/R)"""
        try:
            data = self._make_request(f"people/{pitcher_id}")
            
            if not data or 'people' not in data:
                return 'R'  # Default to right-handed
            
            pitcher_info = data['people'][0]
            pitching_hand = pitcher_info.get('pitchHand', {}).get('code', 'R')
            return pitching_hand
            
        except Exception as e:
            print(f"Error getting pitcher handedness for {pitcher_id}: {e}")
            return 'R'
    
    def get_player_splits(self, player_id: int) -> Dict:
        """Get player's actual batting average for both vs_left and vs_right"""
        try:
            # Get player's actual season batting average for 2025 season
            season_data = self._make_request(f"/people/{player_id}/stats?stats=season&group=hitting&season=2025")
            
            if season_data and 'stats' in season_data and season_data['stats']:
                for stat_group in season_data['stats']:
                    if 'splits' in stat_group and stat_group['splits']:
                        stat = stat_group['splits'][0].get('stat', {})
                        avg_str = stat.get('avg', '')
                        
                        # Parse authentic batting average
                        if avg_str and avg_str not in ['-.---', '', None]:
                            try:
                                batting_avg = float(avg_str)
                                print(f"Player {player_id}: Using authentic BA {batting_avg}")
                                
                                # Use authentic batting average for splits
                                return {
                                    'vs_left': batting_avg,
                                    'vs_right': batting_avg,
                                    'home': batting_avg,
                                    'away': batting_avg
                                }
                            except (ValueError, TypeError):
                                pass
            
            # If we reach here, authentic data was not available
            print(f"Player {player_id}: No authentic batting average available from MLB API")
            return None
            
        except Exception as e:
            print(f"Error getting batting average for player {player_id}: {e}")
            return None
    
    def get_team_recent_offense(self, team_id: int, days_back: int = 10) -> float:
        """Get team's recent offensive performance (runs per game)"""
        try:
            # Use current date for 2025 season
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            data = self._make_request(f"teams/{team_id}/stats", {
                'stats': 'hitting',
                'season': 2025,
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d')
            })
            
            if not data or 'stats' not in data or not data['stats']:
                return 4.5  # League average fallback
            
            stats = data['stats'][0].get('splits', [])
            if not stats:
                return 4.5
            
            team_stats = stats[0].get('stat', {})
            games = float(team_stats.get('gamesPlayed', 1))
            runs = float(team_stats.get('runs', 0))
            
            if games == 0:
                return 4.5
            
            return runs / games
            
        except Exception as e:
            print(f"Error getting team offense for {team_id}: {e}")
            return 4.5
    
    def get_player_status(self, player_id: int) -> Dict:
        """Get player injury status and availability"""
        try:
            endpoint = f"people/{player_id}"
            params = {
                'hydrate': 'currentTeam,stats(type=[yearByYear],season=2025)'
            }
            
            response = self._make_request(endpoint, params)
            if not response or 'people' not in response:
                return {'status': 'unknown', 'is_active': False}
            
            player_data = response['people'][0]
            
            # Check if player is active
            is_active = player_data.get('active', False)
            
            # Get injury status (this field may not always be present)
            injury_status = player_data.get('injuryStatus', None)
            
            return {
                'status': injury_status or 'active' if is_active else 'inactive',
                'is_active': is_active,
                'injury_description': player_data.get('injuryNote', '')
            }
            
        except Exception as e:
            print(f"Error getting status for player {player_id}: {e}")
            return {'status': 'unknown', 'is_active': True}  # Default to active if we can't determine
    
    def get_todays_starting_lineups(self) -> Dict[int, List[int]]:
        """Get confirmed starting lineups for today's games"""
        lineups = {}
        
        try:
            games = self.get_todays_games()
            
            if not games:
                print("No games found for today")
                return lineups
            
            print(f"Checking starting lineups for {len(games)} games...")
            
            for game in games:
                if not isinstance(game, dict) or 'gamePk' not in game:
                    continue
                    
                game_id = game['gamePk']
                game_status = game.get('status', {}).get('detailedState', 'Unknown')
                
                print(f"Game {game_id} status: {game_status}")
                
                # Try multiple endpoints for lineup data
                lineup_found = False
                
                # Method 1: Try lineup endpoint
                lineup_endpoint = f"game/{game_id}/lineup"
                lineup_data = self._make_request(lineup_endpoint)
                
                if lineup_data and 'teams' in lineup_data:
                    for team_side in ['away', 'home']:
                        team_data = lineup_data['teams'].get(team_side, {})
                        team_id = team_data.get('team', {}).get('id')
                        
                        if team_id and 'battingOrder' in team_data:
                            batting_order = team_data['battingOrder']
                            if batting_order:
                                lineups[team_id] = batting_order
                                lineup_found = True
                                print(f"Found starting lineup for team {team_id}: {len(batting_order)} players")
                
                # Method 2: Try boxscore if lineup endpoint didn't work
                if not lineup_found:
                    boxscore_endpoint = f"game/{game_id}/boxscore"
                    boxscore = self._make_request(boxscore_endpoint)
                    
                    if boxscore and 'teams' in boxscore:
                        for team_side in ['away', 'home']:
                            team_data = boxscore['teams'].get(team_side, {})
                            team_id = team_data.get('team', {}).get('id')
                            
                            if team_id:
                                # Get starting players from battingOrder
                                batting_order = team_data.get('battingOrder', [])
                                if batting_order:
                                    lineups[team_id] = batting_order
                                    print(f"Found boxscore lineup for team {team_id}: {len(batting_order)} players")
                
                # Method 3: Try live game data for confirmed starters
                if game_status in ['In Progress', 'Live']:
                    linescore_endpoint = f"game/{game_id}/linescore"
                    linescore = self._make_request(linescore_endpoint)
                    
                    if linescore and 'teams' in linescore:
                        for team_side in ['away', 'home']:
                            team_data = linescore['teams'].get(team_side, {})
                            team_id = team_data.get('team', {}).get('id')
                            
                            if team_id and team_id not in lineups:
                                # Extract confirmed starters from live data
                                players = team_data.get('players', {})
                                if players:
                                    starter_ids = [pid for pid in players.keys() if players[pid].get('battingOrder')]
                                    if starter_ids:
                                        lineups[team_id] = [int(pid.replace('ID', '')) for pid in starter_ids]
                                        print(f"Found live game starters for team {team_id}: {len(starter_ids)} players")
                            
        except Exception as e:
            print(f"Error getting starting lineups: {e}")
        
        total_starters = sum(len(lineup) for lineup in lineups.values())
        print(f"Total confirmed starters found: {total_starters} across {len(lineups)} teams")
        
        return lineups
    
    def filter_active_players(self, rankings_df) -> pd.DataFrame:
        """Filter rankings to only include confirmed starting players using MLB.com lineups"""
        if rankings_df.empty:
            return rankings_df
        
        try:
            print("Filtering to show only confirmed starting players...")
            
            # Try MLB.com lineup scraper first
            from lineup_scraper import MLBLineupScraper
            scraper = MLBLineupScraper()
            starter_names = scraper.get_starter_names_set()
            
            if starter_names:
                print(f"Found {len(starter_names)} confirmed starters from MLB.com")
                
                # Filter by matching player names
                initial_count = len(rankings_df)
                filtered_df = rankings_df[rankings_df['player_name'].isin(starter_names)].copy()
                removed_count = initial_count - len(filtered_df)
                
                print(f"Filtered to {len(filtered_df)} confirmed starters")
                print(f"Removed {removed_count} non-starting players from rankings")
                
                return filtered_df
            
            # Fallback to API-based lineup detection
            lineups = self.get_todays_starting_lineups()
            
            if not lineups:
                print("No confirmed starting lineups available from any source")
                print("Showing all players until lineups are posted")
                return rankings_df
            
            # Get all confirmed starter IDs from API lineups
            starter_player_ids = set()
            for team_id, batting_order in lineups.items():
                starter_player_ids.update(batting_order)
                print(f"Team {team_id} starters: {len(batting_order)} players")
            
            if not starter_player_ids:
                print("No confirmed starters found in lineup data")
                print("Showing all players until lineups are confirmed")
                return rankings_df
            
            # Filter rankings to only include confirmed starters
            initial_count = len(rankings_df)
            filtered_df = rankings_df[rankings_df['player_id'].isin(starter_player_ids)].copy()
            removed_count = initial_count - len(filtered_df)
            
            print(f"Filtered to {len(filtered_df)} confirmed starters")
            print(f"Removed {removed_count} non-starting players from rankings")
            
            return filtered_df
            
        except Exception as e:
            print(f"Error filtering to starting players: {e}")
            print("Showing all players due to filtering error")
            return rankings_df
    
    def _filter_by_player_status(self, rankings_df) -> pd.DataFrame:
        """Fallback method: Filter by individual player injury/active status"""
        try:
            active_players = []
            
            for _, player in rankings_df.iterrows():
                player_id = player['player_id']
                status = self.get_player_status(player_id)
                
                if status.get('is_active', True) and status.get('status', 'active') != 'inactive':
                    active_players.append(player)
                else:
                    print(f"Filtering out {player.get('player_name', 'Unknown')}: {status.get('status', 'inactive')}")
            
            if not active_players:
                print("No active players found via status check - returning original rankings")
                return rankings_df
            
            filtered_df = pd.DataFrame(active_players)
            removed_count = len(rankings_df) - len(filtered_df)
            print(f"Removed {removed_count} players via injury/status check")
            
            return filtered_df
            
        except Exception as e:
            print(f"Error in status-based filtering: {e}")
            return rankings_df
