import sqlite3
import json
import csv
import sys
import os

sys.path.append(os.path.abspath('.'))
from src.processors.run_calculator import calculate_expected_total_runs, make_recommendation, calculate_confidence

def main():
    conn = sqlite3.connect('data/mlb_bot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query all latest predictions with results from June 26th to July 5th
    cursor.execute("""
        SELECT p.*, r.actual_total_runs, r.is_correct 
        FROM predictions p
        LEFT JOIN results r ON p.game_id = r.game_id
        WHERE p.game_date >= '2026-06-26' AND p.game_date <= '2026-07-05' AND p.is_latest = 1
        ORDER BY p.game_date, p.game_time_et
    """)
    rows = cursor.fetchall()
    
    csv_file_path = 'prediction_history_report.csv'
    
    headers = [
        'game_date', 'game_time_et', 'matchup', 'pitcher_away', 'pitcher_home',
        'polymarket_line', 'old_expected_runs', 'old_recommendation', 'old_confidence', 'old_status',
        'new_expected_runs', 'new_recommendation', 'new_confidence', 'new_status', 'actual_runs',
        'old_key_factors', 'new_key_factors'
    ]
    
    count = 0
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for r in rows:
            d = dict(r)
            if not d['raw_stats']:
                continue
                
            raw = json.loads(d['raw_stats'])
            actual = d['actual_total_runs']
            
            # Recalculate with the new code
            analysis = calculate_expected_total_runs(raw)
            new_expected = analysis["final_expected_runs"]
            new_rec = make_recommendation(new_expected, d['polymarket_line'])
            new_conf = calculate_confidence(new_expected, d['polymarket_line'])
            
            # Determine Old Status
            old_rec = d['bot_recommendation']
            if "SKIP" in old_rec:
                old_status = "SKIP"
            elif actual is None:
                old_status = "PENDING"
            else:
                if d['is_correct'] == 1:
                    old_status = "WIN"
                else:
                    old_status = "LOSS"
                    
            # Determine New Status
            if "SKIP" in new_rec:
                new_status = "SKIP"
            elif actual is None:
                new_status = "PENDING"
            else:
                is_over = actual > d['polymarket_line']
                is_under = actual < d['polymarket_line']
                
                predicted_over = "OVER" in new_rec
                predicted_under = "UNDER" in new_rec
                
                if (predicted_over and is_over) or (predicted_under and is_under):
                    new_status = "WIN"
                else:
                    new_status = "LOSS"
                    
            matchup = f"{d['away_team']} @ {d['home_team']}"
            old_factors_str = "; ".join(json.loads(d['key_factors'])) if d['key_factors'] else ""
            new_factors_str = "; ".join(analysis['reasons'])
            
            writer.writerow([
                d['game_date'],
                d['game_time_et'],
                matchup,
                d['pitcher_away'] or "TBD",
                d['pitcher_home'] or "TBD",
                d['polymarket_line'],
                d['bot_expected_runs'],
                d['bot_recommendation'],
                d['bot_confidence'],
                old_status,
                new_expected,
                new_rec,
                new_conf,
                new_status,
                actual if actual is not None else "N/A",
                old_factors_str,
                new_factors_str
            ])
            count += 1
            
    print(f"Successfully generated {csv_file_path} with {count} games.")
    conn.close()

if __name__ == '__main__':
    main()
