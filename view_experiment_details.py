# CARA PAKAI:
#     python view_experiment_details.py              # hari ini
#     python view_experiment_details.py 2026-07-09    # tanggal tertentu

import sqlite3
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

DB_PATH = 'data/mlb_bot.db'
if not os.path.exists(DB_PATH):
    print(f"Error: Database file not found at {DB_PATH}")
    exit(1)

def parse_game_id_string(game_id):
    """
    Untuk game_id format 'AWY_HOM_YYYY-MM-DD_HHMMAM/PM' (dari /prediksi manual
    via telegram_bot.py). Return (away, home, date) atau (None, None, None)
    kalau formatnya tidak cocok (berarti game_id numerik dari main.py).
    """
    m = re.match(r'^([A-Z]{3})_([A-Z]{3})_(\d{4}-\d{2}-\d{2})_', game_id)
    if m:
        return m.group(1), m.group(2), m.group(3)
    return None, None, None

def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
        SELECT
            ep.game_id, ep.params_version, ep.expected_runs, ep.recommendation,
            ep.confidence, ep.volatility_score, ep.logged_at,
            p.home_team, p.away_team, p.game_date, p.polymarket_line
        FROM experiment_predictions ep
        LEFT JOIN predictions p
            ON ep.game_id = p.game_id AND p.is_latest = 1
        WHERE ep.id IN (
            SELECT MAX(id) FROM experiment_predictions GROUP BY game_id, params_version
        )
    """
    try:
        cur.execute(query)
        rows = cur.fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        conn.close()
        exit(1)

    games = defaultdict(dict)
    game_meta = {}

    for r in rows:
        gid = r['game_id']
        parsed_away, parsed_home, parsed_date = parse_game_id_string(gid)

        final_date = r['game_date'] or parsed_date
        final_home = r['home_team'] or parsed_home or "?"
        final_away = r['away_team'] or parsed_away or "?"
        final_line = r['polymarket_line']

        if final_date != target_date:
            continue

        games[gid][r['params_version']] = {
            'runs': r['expected_runs'],
            'rec': r['recommendation'],
            'conf': r['confidence'],
            'vol': r['volatility_score'],
        }
        game_meta[gid] = (final_away, final_home, final_line)

    conn.close()

    print("=" * 78)
    print(f"   DETAIL PREDIKSI TIAP GAME PER VERSI EKSPERIMEN — {target_date}")
    print("=" * 78)

    if not games:
        print(f"\nTidak ada data eksperimen untuk tanggal {target_date}.")
        print("Coba jalankan: python view_experiment_details.py YYYY-MM-DD")
        return

    for gid, versions in games.items():
        away, home, line = game_meta.get(gid, ("?", "?", None))
        print(f"\n🏟️  {away} @ {home}   (Line Polymarket: {line})")
        print(f"    game_id: {gid}")
        print("    " + "-" * 66)
        for ver in sorted(versions.keys()):
            d = versions[ver]
            vol_txt = f" | volatility={d['vol']}" if d['vol'] not in (None, 0) else ""
            conf_txt = d['conf'] or "-"
            print(f"    {ver:28s} | exp={d['runs']:5.2f} | {d['rec']:16s} | conf={conf_txt}{vol_txt}")

    print("\n" + "=" * 78)

if __name__ == "__main__":
    main()
