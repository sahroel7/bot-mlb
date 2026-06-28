import sqlite3

conn = sqlite3.connect('data/mlb_bot.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM daily_performance ORDER BY date DESC LIMIT 30")
rows = cursor.fetchall()

print("Daily Performance History:")
print("-" * 80)
for r in rows:
    row_dict = dict(r)
    print(f"Date: {row_dict['date']}")
    print(f"  Total Games Analyzed: {row_dict['total_games_analyzed']}")
    print(f"  Total Predictions Made: {row_dict['total_predictions_made']}")
    print(f"  Correct: {row_dict['total_correct']} | Incorrect: {row_dict['total_incorrect']}")
    print(f"  Daily Win Rate: {row_dict['win_rate_daily']}%")
    print(f"  Notes: {row_dict['notes']}")
    print("-" * 80)

conn.close()
