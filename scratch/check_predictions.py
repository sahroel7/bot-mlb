import sqlite3
import json

def main():
    conn = sqlite3.connect('data/mlb_bot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get only INCORRECT predictions for 2026-07-04
    cursor.execute("""
        SELECT p.*, r.actual_total_runs, r.went_over, r.is_correct 
        FROM predictions p
        LEFT JOIN results r ON p.game_id = r.game_id
        WHERE p.game_date = '2026-07-04' AND p.is_latest = 1 AND r.is_correct = 0
    """)
    rows = cursor.fetchall()
    print(f"\n--- FAILED predictions for 2026-07-04 (Total: {len(rows)}) ---")
    for r in rows:
        d = dict(r)
        print(f"Matchup: {d['away_team']} @ {d['home_team']}")
        print(f"  Pitchers: {d['pitcher_away']} vs {d['pitcher_home']}")
        print(f"  Line: {d['polymarket_line']} | Bot Expected: {d['bot_expected_runs']} (Gap: {round(d['bot_expected_runs'] - d['polymarket_line'], 2)})")
        print(f"  Rec: {d['bot_recommendation']} | Conf: {d['bot_confidence']}")
        print(f"  Actual Runs: {d['actual_total_runs']} (went {'OVER' if d['went_over'] else 'UNDER'})")
        print(f"  Venue: {d['venue']} | Park Factor: {d['park_factor']}")
        print(f"  Weather: {d['weather_summary']}")
        
        # Parse and print key factors
        try:
            kf = json.loads(d['key_factors'])
            print("  Key Factors:")
            for factor in kf:
                print(f"    - {factor}")
        except:
            print(f"  Key Factors (raw): {d['key_factors']}")
            
        # Parse and print raw_stats if present
        if d['raw_stats']:
            try:
                raw = json.loads(d['raw_stats'])
                # print some pitcher stats
                home_p = raw.get('home_pitcher_stats', {})
                away_p = raw.get('away_pitcher_stats', {})
                print(f"  Home Pitcher Stats: ERA={home_p.get('era')}, FIP={home_p.get('fip')}, WHIP={home_p.get('whip')}, IP={home_p.get('innings_pitched')}")
                print(f"  Away Pitcher Stats: ERA={away_p.get('era')}, FIP={away_p.get('fip')}, WHIP={away_p.get('whip')}, IP={away_p.get('innings_pitched')}")
            except Exception as e:
                print(f"  Error parsing raw_stats: {e}")
                
        print("=" * 80)

    conn.close()

if __name__ == '__main__':
    main()
