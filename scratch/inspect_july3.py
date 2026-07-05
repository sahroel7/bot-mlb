import sqlite3
import json
import sys
import os

sys.path.append(os.path.abspath('.'))
from src.processors.run_calculator import calculate_expected_total_runs, make_recommendation

def main():
    conn = sqlite3.connect('data/mlb_bot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.*, r.actual_total_runs, r.is_correct 
        FROM predictions p
        LEFT JOIN results r ON p.game_id = r.game_id
        WHERE p.game_date = '2026-07-03' AND p.is_latest = 1
    """)
    rows = cursor.fetchall()
    
    print("\n--- DETAILED INSPECTION FOR 2026-07-03 ---")
    for r in rows:
        d = dict(r)
        if not d['raw_stats']:
            continue
            
        raw = json.loads(d['raw_stats'])
        analysis = calculate_expected_total_runs(raw)
        new_rec = make_recommendation(analysis["final_expected_runs"], d['polymarket_line'])
        
        actual = d['actual_total_runs']
        if "SKIP" in new_rec:
            continue
            
        is_over = actual > d['polymarket_line']
        is_under = actual < d['polymarket_line']
        
        predicted_over = "OVER" in new_rec
        predicted_under = "UNDER" in new_rec
        
        status = "WIN ✅" if (predicted_over and is_over) or (predicted_under and is_under) else "LOSS ❌"
        
        print(f"Matchup: {d['away_team']} @ {d['home_team']}")
        print(f"  Line: {d['polymarket_line']} | Expected: {analysis['final_expected_runs']:.2f}")
        print(f"  Rec: {new_rec} | Actual Runs: {actual} | Status: {status}")
        print(f"  Key Reasons: {analysis['reasons']}")
        print("-" * 60)
        
    conn.close()

if __name__ == '__main__':
    main()
