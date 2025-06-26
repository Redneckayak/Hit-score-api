from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from simple_rankings import SimpleMLBRankings
import pandas as pd

app = FastAPI()

# Allow CORS for all domains (safe for now; can restrict later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Hit Score API is live."}

@app.get("/rankings")
def get_rankings(limit: int = 25):
    try:
        rankings = SimpleMLBRankings().get_rankings()
        if rankings.empty:
            return {"error": "No player data available today."}
        top_players = rankings.head(limit)
        return top_players.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}
