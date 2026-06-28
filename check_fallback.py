import sqlite3

conn = sqlite3.connect('data/mlb_bot.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("--- PREDICTIONS WITH THE ODDS API SOURCE ---")
# Let's search for predictions where the source is The Odds API
# In predictions table, the source might be stored in raw_stats or key_factors, or we can search for game_id or questions containing 'Odds'
cursor.execute("""
    SELECT id, game_date, away_team, home_team, bot_recommendation, polymarket_line, predicted_at, game_id
    FROM predictions
    WHERE raw_stats LIKE '%Odds%' OR key_factors LIKE '%Odds%'
    ORDER BY id DESC LIMIT 10
""")
for r in cursor.fetchall():
    print(dict(r))

conn.close()
