import sqlite3
import json

def main():
    conn = sqlite3.connect('data/mlb_bot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get predictions and results for 2026-06-26
    cursor.execute("""
        SELECT p.*, r.actual_total_runs, r.went_over, r.is_correct 
        FROM predictions p
        LEFT JOIN results r ON p.game_id = r.game_id
        WHERE p.game_date = '2026-06-26' AND p.is_latest = 1
    """)
    rows = cursor.fetchall()
    print(f"\n--- Predictions for 2026-06-26 (Total: {len(rows)}) ---")
    for r in rows:
        d = dict(r)
        print(f"Game: {d['away_team']} @ {d['home_team']}")
        print(f"  Line: {d['polymarket_line']} | Expected: {d['bot_expected_runs']}")
        print(f"  Rec: {d['bot_recommendation']} | Conf: {d['bot_confidence']}")
        print(f"  Actual: {d['actual_total_runs']} | Correct: {d['is_correct']}")
        print(f"  Weather: {d['weather_summary']}")
        print(f"  Key Factors: {d['key_factors']}")
        print("-" * 50)

    conn.close()

if __name__ == '__main__':
    main()
