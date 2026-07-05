import sqlite3
import json
from datetime import datetime

def main():
    conn = sqlite3.connect('data/mlb_bot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT game_id, away_team, home_team, game_date, game_time_et, raw_stats 
        FROM predictions 
        WHERE game_date = '2026-07-04' AND is_latest = 1
    """)
    rows = cursor.fetchall()
    print("WEATHER ANALYSIS FOR 2026-07-04 GAMES:")
    print("=" * 80)
    for r in rows:
        d = dict(r)
        print(f"Game: {d['away_team']} @ {d['home_team']} (Time ET: {d['game_time_et']})")
        if d['raw_stats']:
            try:
                raw = json.loads(d['raw_stats'])
                weather = raw.get('weather', {})
                print(f"  Weather object: {weather}")
            except Exception as e:
                print(f"  Error parsing raw_stats: {e}")
        print("-" * 80)

    conn.close()

if __name__ == '__main__':
    main()
