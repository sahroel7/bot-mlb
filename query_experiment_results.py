import sqlite3
import os

# Connect to database
DB_PATH = 'data/mlb_bot.db'
if not os.path.exists(DB_PATH):
    print(f"Error: Database file not found at {DB_PATH}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Query experiment predictions joined with results (only select the latest prediction per game and version)
query = """
    SELECT 
        ep.params_version,
        ep.recommendation,
        r.went_over,
        r.actual_total_runs
    FROM experiment_predictions ep
    JOIN results r ON ep.game_id = r.game_id
    WHERE ep.id IN (
        SELECT MAX(id) 
        FROM experiment_predictions 
        GROUP BY game_id, params_version
    )
"""

try:
    cursor.execute(query)
    rows = cursor.fetchall()
except Exception as e:
    print(f"Error executing query: {e}")
    conn.close()
    exit(1)

# Group results by params_version
stats = {}

for row in rows:
    version = row['params_version']
    rec = row['recommendation']
    went_over = row['went_over']
    
    if version not in stats:
        stats[version] = {
            'total_predictions': 0,
            'bets_made': 0,
            'wins': 0,
            'losses': 0,
            'pushes': 0,
            'skips': 0
        }
    
    stats[version]['total_predictions'] += 1
    
    # Check if recommendation is a bet (OVER/UNDER) or skip
    is_bet = False
    is_win = False
    is_loss = False
    is_push = False
    
    if "OVER" in rec:
        is_bet = True
        if went_over == 1:
            is_win = True
        elif went_over == 0:
            is_loss = True
        else:
            is_push = True
    elif "UNDER" in rec:
        is_bet = True
        if went_over == 0:
            is_win = True
        elif went_over == 1:
            is_loss = True
        else:
            is_push = True
    else:
        # SKIP / NO BET
        stats[version]['skips'] += 1
        
    if is_bet:
        stats[version]['bets_made'] += 1
        if is_win:
            stats[version]['wins'] += 1
        elif is_loss:
            stats[version]['losses'] += 1
        elif is_push:
            stats[version]['pushes'] += 1

# Print analysis summary
print("=" * 80)
print("             MLB BOT SHADOW TESTING PERFORMANCE REPORT")
print("=" * 80)

if not stats:
    print("No experiment prediction results found. Run some games first!")
else:
    for version, data in sorted(stats.items()):
        n = data['bets_made']
        total_games = data['total_predictions']
        wins = data['wins']
        losses = data['losses']
        pushes = data['pushes']
        skips = data['skips']
        
        # Calculate Win Rate: Wins / (Wins + Losses)
        resolved_bets = wins + losses
        win_rate = (wins / resolved_bets * 100.0) if resolved_bets > 0 else 0.0
        
        # Calculate Net Units
        # Assumption payout -110:
        # A win pays +1.0 unit.
        # A loss costs -1.1 units (wagering 1.10 units to win 1.00 unit).
        # A push is returned (0.0 units).
        # You can adjust these values if necessary.
        net_units = (wins * 1.0) - (losses * 1.1)
        
        print(f"Params Version: {version}")
        print(f"  Total Games Analyzed  : {total_games}")
        print(f"  Bets Placed           : {n} (Wins: {wins} | Losses: {losses} | Pushes: {pushes} | Skips: {skips})")
        
        if resolved_bets > 0:
            print(f"  Win Rate              : {win_rate:.2f}%")
            print(f"  Net Units (at -110)   : {net_units:+.2f} units")
        else:
            print("  Win Rate              : 0.00% (No resolved bets)")
            print("  Net Units (at -110)   : +0.00 units")
            
        # Warn if sample size is too small (n < 50)
        if n < 50:
            print(f"  ⚠️ WARNING: Sample size too small (n = {n} < 50). Stats might be volatile!")
            
        print("-" * 80)

conn.close()
