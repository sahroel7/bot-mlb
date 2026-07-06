import sqlite3
import os

DB_PATH = 'data/mlb_bot.db'
if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

try:
    # Check predictions count
    cursor.execute("SELECT COUNT(*) as count FROM predictions")
    pred_count = cursor.fetchone()['count']
    print(f"Total production predictions: {pred_count}")

    # Retrieve last 10 production predictions
    cursor.execute("SELECT id, game_id, predicted_at, bot_recommendation FROM predictions ORDER BY id DESC LIMIT 10")
    pred_rows = cursor.fetchall()
    print("\nLast 10 production predictions:")
    print("-" * 100)
    for row in pred_rows:
        row_dict = dict(row)
        print(f"ID: {row_dict['id']} | Game ID: {row_dict['game_id']} | Recommendation: {row_dict['bot_recommendation']} | Predicted At: {row_dict['predicted_at']}")
    print("-" * 100)

    # Check experiment predictions count
    cursor.execute("SELECT COUNT(*) as count FROM experiment_predictions")
    exp_count = cursor.fetchone()['count']
    print(f"Total experiment predictions: {exp_count}")

    # Retrieve last 10 experiment predictions
    cursor.execute("SELECT * FROM experiment_predictions ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    
    print("\nLast 10 experiment predictions:")
    print("-" * 100)
    for row in rows:
        row_dict = dict(row)
        print(f"ID: {row_dict['id']} | Game ID: {row_dict['game_id']} | Version: {row_dict['params_version']} | Recommendation: {row_dict['recommendation']} | Expected: {row_dict['expected_runs']} | Logged: {row_dict['logged_at']}")
    print("-" * 100)

except Exception as e:
    print(f"Error checking database: {e}")
finally:
    conn.close()
