import sqlite3
import json

def main():
    conn = sqlite3.connect('data/mlb_bot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT away_team, home_team, raw_stats, bot_expected_runs, polymarket_line
        FROM predictions 
        WHERE game_date = '2026-07-04' AND is_latest = 1 AND (away_team LIKE '%Rays%' OR away_team LIKE '%Giants%' OR away_team LIKE '%Mets%')
    """)
    rows = cursor.fetchall()
    for r in rows:
        d = dict(r)
        print(f"=== {d['away_team']} @ {d['home_team']} ===")
        if d['raw_stats']:
            raw = json.loads(d['raw_stats'])
            print("Home Offense (runs_per_game):", raw.get('home_team_stats', {}).get('runs_per_game'))
            print("Away Offense (runs_per_game):", raw.get('away_team_stats', {}).get('runs_per_game'))
            print("Home Team ERA:", raw.get('home_team_stats', {}).get('team_era'))
            print("Away Team ERA:", raw.get('away_team_stats', {}).get('team_era'))
            print("Home Pitcher:", raw.get('home_pitcher_stats'))
            print("Away Pitcher:", raw.get('away_pitcher_stats'))
            print("Bullpen Home ERA:", raw.get('home_bullpen_era'))
            print("Bullpen Away ERA:", raw.get('away_bullpen_era'))
            print("Park Factor:", raw.get('park_factor'))
        print("-" * 80)

    conn.close()

if __name__ == '__main__':
    main()
