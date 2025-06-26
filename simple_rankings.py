import pandas as pd
import json
import os
from datetime import datetime
from data_fetcher import MLBDataFetcher
from data_backup import DataBackupManager


class SimpleMLBRankings:
    def __init__(self):
        self.fetcher = MLBDataFetcher()
        self.cache_file = "data/simple_rankings_cache.json"
        os.makedirs("data", exist_ok=True)

    def calculate_hit_score(self, player_data: dict) -> float:
        """Calculate hit score using simplified weights"""
        try:
            # Player Hotness: (L5 + L10 + L20) / 26.25
            hotness = (player_data["last_5"] + player_data["last_10"] + player_data["last_20"]) / 26.25

            # Pitcher Difficulty: Pitcher OBA / 0.238
            pitcher_factor = player_data.get("pitcher_oba", 0.250) / 0.238

            # Player Skill: Player BA / 0.238
            skill_factor = player_data["batting_avg"] / 0.238

            # Equal weighting (multiply together)
            hit_score = hotness * pitcher_factor * skill_factor

            return round(hit_score, 3)
        except Exception as e:
            print(f"Error calculating hit score: {e}")
            return 0.0

    def generate_daily_rankings(self) -> pd.DataFrame:
        print("Generating daily hit score rankings...")
        games = self.fetcher.get_todays_games()
        if not games:
            print("No games found for today.")
            return pd.DataFrame()

        pitcher_matchups = self.fetcher.get_probable_pitchers(games)
        all_players = []

        for game in games:
            for team_type in ["away", "home"]:
                team_id = game[f"{team_type}_team_id"]
                team_abbr = game[f"{team_type}_team"]

                pitcher_info = pitcher_matchups.get(team_id, {"pitcher_oba": 0.250, "pitcher_name": "TBD"})

                roster = self.fetcher.get_team_roster(team_id)
                for player in roster:
                    try:
                        season_stats = self.fetcher.get_player_season_stats(player["player_id"])
                        recent_stats = self.fetcher.get_player_recent_games(player["player_id"])

                        # Skip players with no recent game activity (Option 3)
                        if (
                            season_stats["games"] == 0
                            or (recent_stats["last_5"] + recent_stats["last_10"] + recent_stats["last_20"]) == 0
                        ):
                            continue

                        player_data = {
                            "player_id": player["player_id"],
                            "player_name": player["player_name"],
                            "team": team_abbr,
                            "position": player["position"],
                            "batting_avg": season_stats["batting_avg"],
                            "last_5": recent_stats["last_5"],
                            "last_10": recent_stats["last_10"],
                            "last_20": recent_stats["last_20"],
                            "games_played": season_stats["games"],
                            "pitcher_oba": pitcher_info["pitcher_oba"],
                            "opposing_pitcher": pitcher_info["pitcher_name"],
                            "is_home": team_type == "home",
                        }

                        player_data["hit_score"] = self.calculate_hit_score(player_data)
                        all_players.append(player_data)

                        print(f"{player['player_name']} - BA: {season_stats['batting_avg']:.3f}")

                    except Exception as e:
                        print(f"Error processing {player['player_name']}: {e}")
                        continue

        if not all_players:
            print("No qualified player data collected.")
            return pd.DataFrame()

        df = pd.DataFrame(all_players).sort_values("hit_score", ascending=False).reset_index(drop=True)

        # Optional filter for active players
        df = self.fetcher.filter_active_players(df)

        df = df.sort_values("hit_score", ascending=False).reset_index(drop=True)

        # Save to cache
        try:
            cache_data = {
                "rankings": df.to_dict("records"),
                "generated_at": datetime.now().isoformat(),
                "total_players": len(df),
            }
            with open(self.cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)
            print(f"Cached {len(df)} player rankings.")
        except Exception as e:
            print(f"Error saving cache: {e}")

        return df

    def load_cached_rankings(self) -> pd.DataFrame:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    cache_data = json.load(f)
                df = pd.DataFrame(cache_data["rankings"])
                print(f"Loaded cached rankings from {cache_data['generated_at']}")
                return df
            except Exception as e:
                print(f"Error loading cache: {e}")
        return pd.DataFrame()

    def _is_cache_expired(self) -> bool:
        try:
            if not os.path.exists(self.cache_file):
                return True

            with open(self.cache_file, "r") as f:
                cache_data = json.load(f)

            if "generated_at" not in cache_data:
                return True

            from datetime import datetime
            import pytz

            cache_time = datetime.fromisoformat(cache_data["generated_at"].replace("Z", "+00:00"))

            cst = pytz.timezone("America/Chicago")
            current_time = datetime.now(cst)

            if cache_time.tzinfo is None:
                cache_time = cst.localize(cache_time)
            else:
                cache_time = cache_time.astimezone(cst)

            today_3am_cst = current_time.replace(hour=3, minute=0, second=0, microsecond=0)
            if current_time.date() > cache_time.date() and current_time >= today_3am_cst:
                return True

            return False
        except Exception as e:
            print(f"Error checking cache expiration: {e}")
            return True

    def get_rankings(self, force_refresh: bool = False) -> pd.DataFrame:
        if not force_refresh:
            cached_df = self.load_cached_rankings()
            if not cached_df.empty and "opposing_pitcher" in cached_df.columns:
                if self._is_cache_expired():
                    print("Cache expired. Regenerating.")
                    return self.generate_daily_rankings()
                return cached_df

        return self.generate_daily_rankings()
