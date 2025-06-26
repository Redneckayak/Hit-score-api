from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def get_hit_scores():
    try:
        print("Returning static test data...")
        result = [
            {
                "player_name": "Shohei Ohtani",
                "team_abbr": "LAD",
                "hit_score": 3.4,
                "batting_avg": 0.328,
                "last_5_hits": 5,
                "last_10_hits": 9,
                "last_20_hits": 18,
                "pitcher_oba": 0.230,
                "batting_order": 2,
                "home_away": "Home"
            },
            {
                "player_name": "Aaron Judge",
                "team_abbr": "NYY",
                "hit_score": 3.1,
                "batting_avg": 0.311,
                "last_5_hits": 4,
                "last_10_hits": 8,
                "last_20_hits": 17,
                "pitcher_oba": 0.250,
                "batting_order": 3,
                "home_away": "Away"
            }
        ]
        return jsonify(result)
    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
