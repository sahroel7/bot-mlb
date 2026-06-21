import sqlite3

conn = sqlite3.connect('data/mlb_bot.db')
c = conn.cursor()
c.execute('''
  SELECT game_date, away_team, home_team, 
         daily_sequence, version, is_latest,
         bot_recommendation
  FROM predictions 
  WHERE game_date >= date('now')
  AND is_latest = 1
  ORDER BY game_date, daily_sequence
  LIMIT 15
''')
rows = c.fetchall()
print("--- SEBELUM UPDATE ---")
for r in rows:
    print(r)
print(f'Total: {len(rows)} rows')

# Ambil semua game per tanggal, beri nomor urut
c.execute('''
  SELECT game_date, game_id 
  FROM predictions 
  WHERE version = 1
  ORDER BY game_date ASC, predicted_at ASC
''')
rows = c.fetchall()

from itertools import groupby
from operator import itemgetter

print("--- PROSES UPDATE ---")
for date, games in groupby(rows, key=itemgetter(0)):
    for seq, (_, game_id) in enumerate(games, start=1):
        c.execute('''
          UPDATE predictions 
          SET daily_sequence = ?
          WHERE game_id = ? AND version = 1
          AND daily_sequence IS NULL
        ''', (seq, game_id))
        c.execute('''
          UPDATE predictions
          SET daily_sequence = ?
          WHERE game_id = ? AND version > 1
          AND daily_sequence IS NULL
        ''', (seq, game_id))

conn.commit()
print('daily_sequence updated')

c.execute('''
  SELECT game_date, away_team, home_team, daily_sequence
  FROM predictions WHERE game_date >= date('now')
  AND is_latest = 1
  ORDER BY game_date, daily_sequence
''')
print("--- SETELAH UPDATE ---")
for r in c.fetchall():
    print(r)
conn.close()
