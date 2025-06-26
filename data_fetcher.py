import requests
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional


class MLBDataFetcher:
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1/"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MLB-Data-Fetcher",
            "Accept": "application/json"
        })
        self.cache_dir = Path("data/player_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.team_lookup = {}
        self._build_team_lookup()

    def _safe_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        try:
            url = f"{self.base_url}{endpoint}"
            res = self.session.get(url, params=params, timeout=10)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"Request failed: {e}")
        return None

    def _build_team_lookup(self):
        data = self._safe_request("teams", {"sportId": 1})
        if data and "teams" in data:
            for team in data["teams"]:
                self.team_lookup[team["id"]] = team.get("abbreviation", "UNK")

    def get_todays_games(self) -> List[dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        data = self._safe_request("schedule", {"sportId": 1, "date": today})
        games = []
        if data and "dates" in data and data["dates"]:
            for game_data in data["dates"][0].get("games", []):
                away_id = game_data["teams"]["away"]["team"]["id"]
                home_id = game_data["teams"]["home"]["team"]["id"]
                games.append({
                    "game_id": game_data["gamePk"],
                    "away_team": self.team_lookup.get(away_id, "UNK"),
                    "home_team": self.team_lookup.get(home_id, "UNK"),
                    "away_team_id": away_id,
                    "home_team_id": home_id
                })
        return games

    def get_team_roster(self, team_id: int) -> List[dict]:
        data = self._safe_request(f"teams/{team_id}/roster", {"rosterType": "active"})
        players = []
        if data and "roster" in data:
            for player in data["roster"]:
                pos = player["position"]["abbreviation"]
                if pos not in ["P", "LHP", "RHP"]:
                    players.append({
                        "player_id": player["person"]["id"],
                        "player_name": player["person"]["fullName"],
                        "position": pos
                    })
        return players

    def _cache_path(self, player_id: int) -> Path:
        return self.cache_dir / f"{player_id}.json"

    def _load_player_cache(self, player_id: int) -> Optional[dict]:
        path = self._cache_path(player_id)
        if not path.exists():
            return None
        with open(path, "r") as f:
            data = json.load(f)
        ts = datetime.fromisoformat(data.get("timestamp", "1900-01-01T00:00:00"))
        if datetime.now() - ts > timedelta(hours=24):
            return None
        return data

    def _save_player_cache(self, player_id: int, data: dict):
        data["timestamp"] = datetime.now().isoformat()
        with open(self._cache_path(player_id), "w") as f:
            json.dump(data, f, indent=2)

    def get_player_season_stats(self, player_id: int) -> dict:
        cached = self._load_player_cache(player_id)
        if cached and "season" in cached:
            return cached["season"]

        stats = {"batting_avg": 0.238, "hits": 0, "at_bats": 0, "games": 0}
        data = self._safe_request(f"people/{player_id}/stats", {
            "stats": "season", "group": "hitting", "season": 2025
        })
        if data and "stats" in data and data["stats"]:
            splits = data["stats"][0].get("splits", [])
            if splits:
                s = splits[0]["stat"]
                stats = {
                    "batting_avg": float(s.get("avg", 0.238)),
                    "hits": int(s.get("hits", 0)),
                    "at_bats": int(s.get("atBats", 0)),
                    "games": int(s.get("gamesPlayed", 0))
                }

        cache = cached if cached else {}
        cache["season"] = stats
        self._save_player_cache(player_id, cache)
        return stats

    def get_player_recent_games(self, player_id: int) -> dict:
        cached = self._load_player_cache(player_id)
        if cached and "recent" in cached:
            return cached["recent"]

        recent = {"last_5": 0, "last_10": 0, "last_20": 0}
        data = self._safe_request(f"people/{player_id}/stats", {
            "stats": "gameLog", "group": "hitting", "season": 2025
        })
        if data and "stats" in data and data["stats"]:
            games = data["stats"][0].get("splits", [])
            games.sort(key=lambda g: g.get("date", ""), reverse=True)
            recent["last_5"] = sum(int(g["stat"].get("hits", 0)) for g in games[:5])
            recent["last_10"] = sum(int(g["stat"].get("hits", 0)) for g in games[:10])
            recent["last_20"] = sum(int(g["stat"].get("hits", 0)) for g in games[:20])

        cache = cached if cached else {}
        cache["recent"] = recent
        self._save_player_cache(player_id, cache)
        return recent

    def get_pitcher_oba(self, pitcher_id: int) -> float:
        cached = self._load_player_cache(pitcher_id)
        if cached and "pitcher_oba" in cached:
            return cached["pitcher_oba"]

        oba = 0.250
        data = self._safe_request(f"people/{pitcher_id}/stats", {
            "stats": "season", "group": "pitching", "season": 2025
        })
        if data and "stats" in data and data["stats"]:
            splits = data["stats"][0].get("splits", [])
            if splits:
                oba = float(splits[0].get("stat", {}).get("avg", 0.250))

        cache = cached if cached else {}
        cache["pitcher_oba"] = oba
        self._save_player_cache(pitcher_id, cache)
        return oba

    def get_probable_pitchers(self, games: List[dict]) -> dict:
        matchups = {}
        for game in games:
            data = self._safe_request("schedule", {"gamePk": game["game_id"], "hydrate": "probablePitcher"})
            if data and "dates" in data:
                for d in data["dates"]:
                    for g in d.get("games", []):
                        if g["gamePk"] == game["game_id"]:
                            away = g["teams"]["away"].get("probablePitcher")
                            home = g["teams"]["home"].get("probablePitcher")
                            if home:
                                matchups[game["away_team_id"]] = {
                                    "pitcher_id": home["id"],
                                    "pitcher_name": home["fullName"],
                                    "pitcher_oba": self.get_pitcher_oba(home["id"])
                                }
                            if away:
                                matchups[game["home_team_id"]] = {
                                    "pitcher_id": away["id"],
                                    "pitcher_name": away["fullName"],
                                    "pitcher_oba": self.get_pitcher_oba(away["id"])
                                }
        return matchups

    def filter_active_players(self, df: pd.DataFrame) -> pd.DataFrame:
        return df
