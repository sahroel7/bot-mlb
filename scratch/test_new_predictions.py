import sqlite3
import json
import sys
import os

sys.path.append(os.path.abspath('.'))
from src.processors.run_calculator import calculate_expected_total_runs, make_recommendation, calculate_confidence

def main():
    conn = sqlite3.connect('data/mlb_bot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.*, r.actual_total_runs, r.is_correct 
        FROM predictions p
        LEFT JOIN results r ON p.game_id = r.game_id
        WHERE p.game_date = '2026-07-04' AND p.is_latest = 1
    """)
    rows = cursor.fetchall()
    
    print("COMPARISON: OLD VS NEW BOT PREDICTIONS FOR 2026-07-04")
    print("=" * 100)
    print(f"{'Matchup':<35} | {'Line':<4} | {'Old Rec':<10} | {'New Rec':<10} | {'Actual':<6} | {'New Status'}")
    print("-" * 100)
    
    for r in rows:
        d = dict(r)
        if not d['raw_stats']:
            continue
            
        raw = json.loads(d['raw_stats'])
        
        # Recalculate with the new code
        analysis = calculate_expected_total_runs(raw)
        new_rec = make_recommendation(analysis["final_expected_runs"], d['polymarket_line'])
        new_conf = calculate_confidence(analysis["final_expected_runs"], d['polymarket_line'])
        
        # Check if the new prediction is correct
        actual = d['actual_total_runs']
        if actual is None:
            new_status = "No Result"
        else:
            if "SKIP" in new_rec:
                new_status = "SKIP ⚠️"
            else:
                is_over = actual > d['polymarket_line']
                is_under = actual < d['polymarket_line']
                
                predicted_over = "OVER" in new_rec
                predicted_under = "UNDER" in new_rec
                
                if (predicted_over and is_over) or (predicted_under and is_under):
                    new_status = "WIN ✅"
                else:
                    new_status = "LOSS ❌"
                    
        matchup = f"{d['away_team']} @ {d['home_team']}"
        old_rec = f"{d['bot_recommendation']} ({d['bot_confidence'].split(' ')[0]})"
        new_rec_str = f"{new_rec.split(' ')[0]} ({new_conf.split(' ')[0]})"
        
        print(f"{matchup:<35} | {d['polymarket_line']:<4} | {old_rec:<10} | {new_rec_str:<10} | {actual:<6} | {new_status}")
        
    conn.close()

if __name__ == '__main__':
    main()
