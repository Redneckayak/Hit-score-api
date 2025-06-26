import requests
from datetime import datetime
import os


class MLBDataFetcher:
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1/"
        self.team_lookup = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MLB-HitScoreApp/1.0',
            'Accept': 'application/json'
        })
        self._build_team_lookup()

    def _safe_request(self, endpoint, params=None):
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Request failed: {e}")
        return None

    def _build_team_lookup(self):
        data = self._safe_request("teams", {"sportId": 1})
        if data and "teams" in data:
            for team in data["teams"]:
                self.team_lookup[team["id"]] = team.get("abbreviation", "UNK")

    def get_todays_games(self):
        today = datetime.now().strftime("%Y-%m-%d")
        data = self._safe_request("schedule", {"sportId": 1, "date": today})
        games = []

        if data and "dates" in data and data["dates"]:
            for game_data in data["dates"][0].get("games", []):
                try:
                    away_team_id = game_data["teams"]["away"]["team"]["id"]
                    home_team_id = game_data["teams"]["home"]["team"]["id"]

                    games.append({
                        "game_id": game_data["gamePk"],
                        "away_team": self.team_lookup.get(away_team_id, "UNK"),
                        "home_team": self.team_lookup.get(home_team_id, "UNK"),
                        "away_team_id": away_team_id,
                        "home_team_id": home_team_id
                    })
                except Exception as e:
                    print(f"Error parsing game data: {e}")
        return games

    def get_team_roster(self, team_id):
        data = self._safe_request(f"teams/{team_id}/roster", {"rosterType": "active"})
        roster = []

        if data and "roster" in data:
            for player_data in data["roster"]:
                position = player_data["position"]["abbreviation"]
                if position not in ["P", "LHP", "RHP"]:
                    roster.append({
                        "player_id": player_data["person"]["id"],
                        "player_name": player_data["person"]["fullName"],
                        "position": position
                    })
        return roster

    def get_player_season_stats(self, player_id):
        data = self._safe_request(f"people/{player_id}/stats", {
            "stats": "season",
            "group": "hitting",
            "season": 2025
        })

        if data and "stats" in data and data["stats"]:
            splits = data["stats"][0].get("splits", [])
            if splits:
                stat = splits[0]["stat"]
                return {
                    "batting_avg": float(stat.get("avg", 0.238)),
                    "hits": int(stat.get("hits", 0)),
                    "at_bats": int(stat.get("atBats", 0)),
                    "games": int(stat.get("gamesPlayed", 0))
                }

        return {"batting_avg": 0.238, "hits": 0, "at_bats": 0, "games": 0}

    def get_player_recent_games(self, player_id):
        data = self._safe_request(f"people/{player_id}/stats", {
            "stats": "gameLog",
            "group": "hitting",
            "season": 2025
        })

        recent = {"last_5": 0, "last_10": 0, "last_20": 0}

        if data and "stats" in data and data["stats"]:
            logs = data["stats"][0].get("splits", [])
            logs.sort(key=lambda x: x.get("date", ""), reverse=True)

            recent["last_5"] = sum(int(game["stat"].get("hits", 0)) for game in logs[:5])
            recent["last_10"] = sum(int(game["stat"].get("hits", 0)) for game in logs[:10])
            recent["last_20"] = sum(int(game["stat"].get("hits", 0)) for game in logs[:20])

        return recent

    def get_pitcher_oba(self, pitcher_id):
        data = self._safe_request(f"people/{pitcher_id}/stats", {
            "stats": "season",
            "group": "pitching",
            "season": 2025
        })

        if data and "stats" in data and data["stats"]:
            splits = data["stats"][0].get("splits", [])
            if splits:
                stat = splits[0]["stat"]
                return float(stat.get("avg", 0.250))

        return 0.250

    def get_probable_pitchers(self, games: list) -> dict:
        """Get probable starting pitchers for today's games."""
        pitcher_matchups = {}

        for game in games:
            data = self._safe_request("schedule", {
                "gamePk": game["game_id"],
                "hydrate": "probablePitcher"
            })

            if data and "dates" in data:
                for date_data in data["dates"]:
                    for game_info in date_data.get("games", []):
                        if game_info["gamePk"] == game["game_id"]:
                            home_pitcher = game_info.get("teams", {}).get("home", {}).get("probablePitcher")
                            away_pitcher = game_info.get("teams", {}).get("away", {}).get("probablePitcher")

                            if home_pitcher:
                                pitcher_matchups[game["away_team_id"]] = {
                                    "pitcher_name": home_pitcher.get("fullName", "TBD"),
                                    "pitcher_oba": self.get_pitcher_oba(home_pitcher["id"])
                                }

                            if away_pitcher:
                                pitcher_matchups[game["home_team_id"]] = {
                                    "pitcher_name": away_pitcher.get("fullName", "TBD"),
                                    "pitcher_oba": self.get_pitcher_oba(away_pitcher["id"])
                                }

        return pitcher_matchups

    def filter_active_players(self, df):
        """Placeholder for filtering logic if needed"""
        return df  # You can later integrate injury report or lineup filter here
