from flask import Flask, jsonify
from simple_rankings import SimpleMLBRankings

app = Flask(__name__)

@app.route("/")
def get_hit_scores():
    try:
        print("Loading real Hit Score data...")
        rankings_df = SimpleMLBRankings().get_rankings()

        if rankings_df is None or rankings_df.empty:
            return jsonify({"error": "No data available"}), 500

        output = rankings_df[[
            'player_name', 'team', 'hit_score', 'batting_avg',
            'last_5', 'last_10', 'last_20', 'pitcher_oba',
            'opposing_pitcher', 'position', 'is_home'
        ]].copy()

        result = output.to_dict(orient="records")
        return jsonify(result)

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
