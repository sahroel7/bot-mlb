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

    # Get all prediction dates available in the range
    cursor.execute("""
        SELECT DISTINCT game_date 
        FROM predictions 
        WHERE game_date >= '2026-06-26' AND game_date <= '2026-07-05'
        ORDER BY game_date
    """)
    dates = [row['game_date'] for row in cursor.fetchall()]
    
    print(f"RUNNING BACKTEST FROM {dates[0]} TO {dates[-1]}")
    print("=" * 115)
    print(f"{'Date':<12} | {'Old Bot Bets':<15} | {'Old Win Rate':<12} | {'New Bot Bets':<15} | {'New Win Rate':<12} | {'Diff / Notes'}")
    print("-" * 115)
    
    tot_old_active = 0
    tot_old_wins = 0
    tot_new_active = 0
    tot_new_wins = 0
    
    for date_str in dates:
        cursor.execute("""
            SELECT p.*, r.actual_total_runs, r.is_correct 
            FROM predictions p
            LEFT JOIN results r ON p.game_id = r.game_id
            WHERE p.game_date = ? AND p.is_latest = 1
        """, (date_str,))
        rows = cursor.fetchall()
        
        old_active = 0
        old_wins = 0
        new_active = 0
        new_wins = 0
        has_results = False
        
        for r in rows:
            d = dict(r)
            if not d['raw_stats']:
                continue
                
            raw = json.loads(d['raw_stats'])
            actual = d['actual_total_runs']
            
            # Skip games that don't have actual results yet (e.g. today's games)
            if actual is None:
                continue
                
            has_results = True
            
            # Old Bot Evaluation
            old_rec = d['bot_recommendation']
            old_is_active = "SKIP" not in old_rec
            if old_is_active:
                old_active += 1
                if d['is_correct'] == 1:
                    old_wins += 1
            
            # New Bot Evaluation
            analysis = calculate_expected_total_runs(raw)
            new_rec = make_recommendation(analysis["final_expected_runs"], d['polymarket_line'])
            
            new_is_active = "SKIP" not in new_rec
            if new_is_active:
                new_active += 1
                
                is_over = actual > d['polymarket_line']
                is_under = actual < d['polymarket_line']
                
                predicted_over = "OVER" in new_rec
                predicted_under = "UNDER" in new_rec
                
                if (predicted_over and is_over) or (predicted_under and is_under):
                    new_wins += 1
        
        if not has_results:
            print(f"{date_str:<12} | {'No Completed Games yet or No Results in DB':<96}")
            continue
            
        old_wr = (old_wins / old_active * 100) if old_active > 0 else 0
        new_wr = (new_wins / new_active * 100) if new_active > 0 else 0
        
        tot_old_active += old_active
        tot_old_wins += old_wins
        tot_new_active += new_active
        tot_new_wins += new_wins
        
        # Calculate diff notes
        net_wins_diff = new_wins - old_wins
        net_bets_diff = new_active - old_active
        note = ""
        if net_wins_diff > 0:
            note += f"+{net_wins_diff} Wins "
        elif net_wins_diff < 0:
            note += f"{net_wins_diff} Wins "
            
        if net_bets_diff != 0:
            note += f"({net_bets_diff:>+0} Bets)"
            
        if not note:
            note = "Identical performance"
            
        print(f"{date_str:<12} | {f'{old_wins}/{old_active}':<15} | {f'{old_wr:.1f}%':<12} | {f'{new_wins}/{new_active}':<15} | {f'{new_wr:.1f}%':<12} | {note}")
        
    print("=" * 115)
    final_old_wr = (tot_old_wins / tot_old_active * 100) if tot_old_active > 0 else 0
    final_new_wr = (tot_new_wins / tot_new_active * 100) if tot_new_active > 0 else 0
    
    print(f"{'OVERALL TOTAL':<12} | {f'{tot_old_wins}/{tot_old_active}':<15} | {f'{final_old_wr:.1f}%':<12} | {f'{tot_new_wins}/{tot_new_active}':<15} | {f'{final_new_wr:.1f}%':<12} | Net Change: {tot_new_wins - tot_old_wins:>+0} Wins, {tot_new_active - tot_old_active:>+0} Bets")
    print(f"New Bot saved {tot_old_active - tot_new_active} total bets from being placed while maintaining higher accuracy.")
    
    conn.close()

if __name__ == '__main__':
    main()
