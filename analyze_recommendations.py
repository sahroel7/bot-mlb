import sqlite3
from collections import defaultdict

conn = sqlite3.connect('data/mlb_bot.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

query = """
SELECT 
    bot_recommendation,
    is_correct,
    COUNT(*) as count
FROM predictions p
LEFT JOIN results r ON p.game_id = r.game_id
WHERE p.is_latest = 1 AND r.actual_total_runs IS NOT NULL
GROUP BY bot_recommendation, is_correct
"""

cursor.execute(query)
rows = cursor.fetchall()

stats = defaultdict(lambda: {"won": 0, "lost": 0, "total": 0})
skip_stats = {"went_over": 0, "went_under": 0, "total": 0}

for row in rows:
    rec = row['bot_recommendation']
    is_correct = row['is_correct']
    count = row['count']
    
    rec_clean = "SKIP" if "SKIP" in rec else ("OVER" if "OVER" in rec else "UNDER")
    
    if rec_clean != "SKIP":
        if is_correct == 1:
            stats[rec_clean]["won"] += count
        elif is_correct == 0:
            stats[rec_clean]["lost"] += count
        stats[rec_clean]["total"] += count

# Let's query SKIP details separately
cursor.execute("""
SELECT 
    p.polymarket_line,
    r.actual_total_runs,
    COUNT(*) as count
FROM predictions p
JOIN results r ON p.game_id = r.game_id
WHERE p.is_latest = 1 AND p.bot_recommendation LIKE '%SKIP%' AND r.actual_total_runs IS NOT NULL
GROUP BY p.polymarket_line, r.actual_total_runs
""")
skip_rows = cursor.fetchall()
for row in skip_rows:
    line = row['polymarket_line']
    actual = row['actual_total_runs']
    count = row['count']
    if actual > line:
        skip_stats["went_over"] += count
    else:
        skip_stats["went_under"] += count
    skip_stats["total"] += count

print("=== HISTORICAL PREDICTION PERFORMANCE ANALYSIS ===")
print("-" * 50)
for rec, data in stats.items():
    win_rate = (data["won"] / data["total"] * 100) if data["total"] > 0 else 0
    print(f"Recommendation: {rec}")
    print(f"  Total Bets: {data['total']}")
    print(f"  Won: {data['won']}")
    print(f"  Lost: {data['lost']}")
    print(f"  Win Rate: {win_rate:.2f}%")
    print("-" * 50)

skip_over_rate = (skip_stats["went_over"] / skip_stats["total"] * 100) if skip_stats["total"] > 0 else 0
print("Recommendation: SKIP / NO BET")
print(f"  Total Skipped Games: {skip_stats['total']}")
print(f"  Actually Went OVER the line: {skip_stats['went_over']} ({skip_over_rate:.2f}%)")
print(f"  Actually Went UNDER the line: {skip_stats['went_under']} ({100 - skip_over_rate:.2f}%)")
print("-" * 50)

conn.close()
