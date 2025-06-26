from flask import Flask, jsonify
from daily_cache import DailyCacheManager

app = Flask(__name__)
cache_manager = DailyCacheManager()

@app.route("/")
def get_hit_scores():
    try:
        print("Calling DailyCacheManager...")
        rankings_df = cache_manager.get_complete_rankings()

        if rankings_df is None or rankings_df.empty:
            print("No data returned.")
            return jsonify({"error": "No data available"}), 500

        output = rankings_df[[
            'player_name', 'team_abbr', 'hit_score', 'batting_avg',
            'last_5_hits', 'last_10_hits', 'last_20_hits',
            'pitcher_oba', 'batting_order', 'home_away'
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
