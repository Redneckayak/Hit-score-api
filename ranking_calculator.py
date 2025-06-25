import pandas as pd
import numpy as np
from typing import Dict

class RankingCalculator:
    """Calculates power rankings for MLB hitters"""
    
    def __init__(self):
        # Constants for normalized scoring
        self.avg_hits_per_game = 0.75  # Average hitter gets 0.75 hits per game
        self.league_avg_ba = 0.238     # League average batting average

    
    def normalize_hits(self, hits: int, games: int, max_games: int) -> float:
        """Normalize hit counts to a 0-10 scale based on games played"""
        if games == 0:
            return 0.0
        
        # For hot hitters, we want to reward high absolute hit counts more aggressively
        # Use a combination of total hits and hits per game
        actual_games = min(games, max_games)
        hits_per_game = hits / actual_games
        
        # Bonus scoring for hot hitters: 8+ hits in 5 games gets significant boost
        if max_games == 5 and hits >= 8:
            base_score = 9.0 + (hits - 8) * 0.5  # 8 hits = 9.0, 9 hits = 9.5, etc.
        elif max_games == 5 and hits >= 6:
            base_score = 7.0 + (hits - 6) * 1.0  # 6 hits = 7.0, 7 hits = 8.0
        else:
            # Standard scoring based on hits per game
            base_score = (hits_per_game / 0.5) * 10
        
        return min(base_score, 10.0)
    
    def normalize_pitcher_oba(self, oba: float) -> float:
        """Normalize pitcher OBA to a 0-10 scale (higher OBA = easier pitcher)"""
        if oba <= 0:
            return 5.0  # Default middle value
        
        # OBA typically ranges from 0.200 to 0.350
        # Minimal impact: use very narrow range 4.8 to 5.2 to almost eliminate pitcher bias
        # This makes individual hitter performance the primary factor
        normalized = ((oba - 0.200) / 0.150) * 0.4 + 4.8
        
        return max(4.8, min(normalized, 5.2))
    
    def normalize_batting_order(self, batting_order: int) -> float:
        """Normalize batting order to a 0-10 scale (lower order = higher score)"""
        if batting_order <= 0 or batting_order > 9:
            return 5.0  # Default middle value for unknown positions
        
        # Batting order 1-9: 1st = 10.0, 2nd = 8.75, 3rd = 7.5, etc.
        # Linear decrease from 10.0 to 1.25
        normalized = 10.0 - ((batting_order - 1) * 1.25)
        
        return max(1.25, min(normalized, 10.0))
    
    def calculate_matchup_advantage(self, player_splits: dict, pitcher_hand: str, is_home: bool) -> float:
        """Calculate advantage based on L/R matchup and home/away splits"""
        # Left/Right matchup advantage
        player_avg_vs_pitcher = 0.0
        if pitcher_hand == 'L':
            player_avg_vs_pitcher = player_splits.get('vs_left', 0.0)
        else:
            player_avg_vs_pitcher = player_splits.get('vs_right', 0.0)
        
        # Home/Away advantage
        home_away_avg = 0.0
        if is_home:
            home_away_avg = player_splits.get('home', 0.0)
        else:
            home_away_avg = player_splits.get('away', 0.0)
        
        # Convert batting averages to 0-10 scale
        # .300+ = 9-10, .250-.299 = 6-8, .200-.249 = 3-5, <.200 = 0-2
        lr_score = min(10.0, max(0.0, (player_avg_vs_pitcher - 0.150) * 20))
        ha_score = min(10.0, max(0.0, (home_away_avg - 0.150) * 20))
        
        return (lr_score + ha_score) / 2
    
    def normalize_team_offense(self, runs_per_game: float) -> float:
        """Normalize team offensive momentum to 0-10 scale"""
        # League average is around 4.5 runs per game
        # 6+ RPG = hot (8-10), 4-6 RPG = average (5-7), <4 RPG = cold (0-4)
        if runs_per_game >= 6.0:
            return 8.0 + min(2.0, (runs_per_game - 6.0) * 0.5)
        elif runs_per_game >= 4.0:
            return 5.0 + (runs_per_game - 4.0) * 1.5
        else:
            return max(0.0, runs_per_game * 1.25)
    
    def calculate_hit_score(self, row: pd.Series) -> float:
        """Calculate hit score using normalized factors"""
        try:
            # 1. Player Hotness: L5 + L10 + L20 (weighted toward recent games) divided by expected hits
            # This gives 3x weight to last 5 games, 2x weight to games 6-10, 1x weight to games 11-20
            weighted_hits = float(row['hits_last_5'] + row['hits_last_10'] + row['hits_last_20'])
            # Expected hits: (5*3 + 5*2 + 10*1) * 0.75 = (15 + 10 + 10) * 0.75 = 26.25
            expected_hits = 35 * self.avg_hits_per_game  # 35 weighted games * 0.75 hits per game = 26.25
            hotness_factor = weighted_hits / expected_hits
            
            # 2. Pitcher Difficulty: Pitcher OBA divided by league average
            pitcher_oba_raw = row.get('pitcher_oba', self.league_avg_ba)
            pitcher_oba = float(pitcher_oba_raw) if pitcher_oba_raw is not None else self.league_avg_ba
            pitcher_factor = pitcher_oba / self.league_avg_ba
            
            # 3. Batter Splits: Use appropriate split vs pitcher hand, normalized by league average
            pitcher_hand = row.get('pitcher_hand', 'R')
            player_splits = row.get('player_splits', {})
            
            if isinstance(player_splits, dict):
                if pitcher_hand == 'L':
                    split_avg = float(player_splits.get('vs_left', self.league_avg_ba))
                else:
                    split_avg = float(player_splits.get('vs_right', self.league_avg_ba))
            else:
                split_avg = self.league_avg_ba
            
            splits_factor = split_avg / self.league_avg_ba
            
            # Combine all three factors equally (multiply them together)
            hit_score = hotness_factor * pitcher_factor * splits_factor
            
            return round(hit_score, 3)
            
        except Exception as e:
            print(f"Error calculating hit score: {e}")
            return 0.0
    
    def calculate_rankings(self, hitter_stats: pd.DataFrame, pitcher_matchups: Dict[int, Dict]) -> pd.DataFrame:
        """Calculate power rankings combining hitter stats and pitcher matchups"""
        if hitter_stats.empty:
            return pd.DataFrame()
        
        # Merge hitter stats with pitcher matchups
        rankings_data = []
        
        for _, hitter in hitter_stats.iterrows():
            team_id = int(hitter['team_id'])
            player_id = int(hitter['player_id'])
            
            # Get pitcher matchup info
            matchup_info = pitcher_matchups.get(team_id, {
                'opposing_pitcher': 'TBD',
                'opposing_pitcher_id': None,
                'pitcher_oba': 0.250,
                'pitcher_hand': 'R',
                'opponent_team': 'TBD',
                'team_offense': 4.5,
                'is_home': True
            })
            
            # Skip players whose teams don't have games today
            if matchup_info['opposing_pitcher'] == 'TBD':
                continue
            

            
            # Get actual player splits from data fetcher
            from data_fetcher import MLBDataFetcher
            data_fetcher = MLBDataFetcher()
            player_splits = data_fetcher.get_player_splits(player_id)
            
            # Skip players without authentic batting average data
            if player_splits is None:
                continue
            
            # Combine hitter and matchup data
            ranking_row = {
                'player_id': player_id,
                'player_name': hitter['player_name'],
                'team': hitter['team'],
                'team_abbr': hitter['team'],  # Add team_abbr for logo display
                'position': hitter['position'],
                'hits_last_5': hitter['hits_last_5'],
                'hits_last_10': hitter['hits_last_10'],
                'hits_last_20': hitter['hits_last_20'],
                'games_played': hitter['games_played'],
                'opposing_pitcher': matchup_info['opposing_pitcher'],
                'opponent_team': matchup_info['opponent_team'],
                'pitcher_hand': matchup_info.get('pitcher_hand', 'R'),
                'vs_LHP': player_splits.get('vs_left', 0.238),
                'vs_RHP': player_splits.get('vs_right', 0.238),
                'is_home': matchup_info.get('is_home', True),
                'pitcher_oba': matchup_info['pitcher_oba'],
                'batting_avg': player_splits.get('batting_avg', 0.238),  # Add for display
                'batting_order': matchup_info.get('batting_order', 9),  # Add batting order
                'home_away': 'H' if matchup_info.get('is_home', True) else 'A',  # Add H/A indicator
                'player_splits': player_splits  # Used for calculation only, not displayed
            }
            
            rankings_data.append(ranking_row)
        
        # Create DataFrame
        rankings_df = pd.DataFrame(rankings_data)
        
        if rankings_df.empty:
            return rankings_df
        

        
        # Calculate hit scores using new formula
        rankings_df['hit_score'] = rankings_df.apply(self.calculate_hit_score, axis=1)
        
        # Sort by hit score (descending)
        rankings_df = rankings_df.sort_values('hit_score', ascending=False).reset_index(drop=True)
        
        return rankings_df
    
    def get_ranking_explanation(self) -> str:
        """Get explanation of ranking methodology"""
        return f"""
        **Hit Score Formula (Simplified & Balanced):**
        
        **Three Equal Factors:**
        1. **Player Hotness**: (L5 + L10 + L20) ÷ 26.25 (expected weighted hits for average player)
           - L5 gets 3x weight, L10 gets 2x weight, L20 gets 1x weight
           - Assumes average hitter gets {self.avg_hits_per_game} hits per game
           
        2. **Pitcher Difficulty**: Pitcher's OBA ÷ {self.league_avg_ba} (league average)
           - Higher pitcher OBA = easier matchup = higher score
           
        3. **Batter Splits vs Hand**: Player's batting average vs pitcher handedness ÷ {self.league_avg_ba}
           - Uses vs LHP or vs RHP split based on opposing pitcher
           
        **Final Score**: Hotness Factor × Pitcher Factor × Splits Factor
        
        Each factor is normalized to league average, creating equal weighting without manual adjustments.
        """
