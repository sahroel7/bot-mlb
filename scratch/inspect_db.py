import sqlite3

def main():
    conn = sqlite3.connect('data/mlb_bot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row['name'] for row in cursor.fetchall()]
    print("Tables in db:", tables)
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        count = cursor.fetchone()['count']
        print(f"Table '{table}' has {count} rows")
        
    # Let's see some predictions
    cursor.execute("SELECT * FROM predictions LIMIT 5")
    rows = cursor.fetchall()
    print("\n--- SAMPLE PREDICTIONS ---")
    for r in rows:
        print(dict(r))
        
    # Let's see some results
    cursor.execute("SELECT * FROM results LIMIT 5")
    rows = cursor.fetchall()
    print("\n--- SAMPLE RESULTS ---")
    for r in rows:
        print(dict(r))

    # Let's see if results and predictions match
    cursor.execute("SELECT count(*) as count FROM predictions p JOIN results r ON p.game_id = r.game_id")
    match_count = cursor.fetchone()['count']
    print(f"\nMatched predictions and results: {match_count}")
    
    # Check predictions where is_latest is set
    cursor.execute("SELECT is_latest, COUNT(*) as count FROM predictions GROUP BY is_latest")
    for r in cursor.fetchall():
        print(f"is_latest={r['is_latest']}: {r['count']} rows")
        
    # Check if results have actual_total_runs not null
    cursor.execute("SELECT COUNT(*) as count FROM results WHERE actual_total_runs IS NOT NULL")
    print(f"Results with actual_total_runs not null: {cursor.fetchone()['count']}")
    
    conn.close()

if __name__ == "__main__":
    main()
