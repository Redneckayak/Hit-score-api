from fastapi import FastAPI
from simple_rankings import SimpleMLBRankings

# Create FastAPI app
app = FastAPI()

# Initialize rankings generator
rankings = SimpleMLBRankings()

# Root endpoint to confirm it's live
@app.get("/")
def read_root():
    return {"message": "Hit Score API is live!"}

# ✅ Health check endpoint for Render
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Endpoint to get daily rankings
@app.get("/rankings")
def get_rankings():
    df = rankings.get_rankings(force_refresh=True)
    top_players = df[[
        "player_name",
        "team",
        "batting_avg",
        "last_5",
        "last_10",
        "last_20",
        "pitcher_oba",
        "hit_score"
    ]].head(25)
    return top_players.to_dict(orient="records")
