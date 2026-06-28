"""
Modul Bullpen Collector (Phase 4 Reliability).
Menggunakan Bullpen CLI sebagai sumber odds harian.
Mendukung caching 30 menit di SQLite dan sinkronisasi ET.
"""

import subprocess
import json
import re
import os
import time
import sqlite3
import difflib
from datetime import datetime, timedelta
import pytz
from src.utils.logger import logger

DB_PATH = 'data/mlb_bot.db'

# Mapping Nama Tim Polymarket/Bullpen -> Nama Resmi MLB API
TEAM_NAME_MAP = {
    "Diamondbacks": "Arizona Diamondbacks",
    "Braves": "Atlanta Braves",
    "Orioles": "Baltimore Orioles",
    "Red Sox": "Boston Red Sox",
    "Cubs": "Chicago Cubs",
    "White Sox": "Chicago White Sox",
    "Reds": "Cincinnati Reds",
    "Guardians": "Cleveland Guardians",
    "Rockies": "Colorado Rockies",
    "Tigers": "Detroit Tigers",
    "Astros": "Houston Astros",
    "Royals": "Kansas City Royals",
    "Angels": "Los Angeles Angels",
    "Dodgers": "Los Angeles Dodgers",
    "Marlins": "Miami Marlins",
    "Brewers": "Milwaukee Brewers",
    "Twins": "Minnesota Twins",
    "Mets": "New York Mets",
    "Yankees": "New York Yankees",
    "Athletics": "Oakland Athletics",
    "Phillies": "Philadelphia Phillies",
    "Pirates": "Pittsburgh Pirates",
    "Padres": "San Diego Padres",
    "Giants": "San Francisco Giants",
    "Mariners": "Seattle Mariners",
    "Cardinals": "St. Louis Cardinals",
    "Rays": "Tampa Bay Rays",
    "Rangers": "Texas Rangers",
    "Blue Jays": "Toronto Blue Jays",
    "Nationals": "Washington Nationals"
}

OFFICIAL_TEAMS = list(TEAM_NAME_MAP.values())

def get_official_team_name(name):
    """Mengonversi nama tim Bullpen ke nama resmi MLB API."""
    name = name.strip()
    # 1. Cek mapping langsung
    if name in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[name]
    
    # 2. Cek jika sudah nama resmi
    if name in OFFICIAL_TEAMS:
        return name
        
    # 3. Fuzzy matching sebagai fallback
    matches = difflib.get_close_matches(name, OFFICIAL_TEAMS, n=1, cutoff=0.6)
    if matches:
        return matches[0]
        
    return name

def init_cache_db():
    """Memastikan tabel cache tersedia."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS market_cache 
                     (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)''')
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"[Bullpen Cache] Init error: {e}")

def get_cached_markets(key):
    """Mengambil data dari cache jika masih valid (30 menit)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT value, updated_at FROM market_cache WHERE key = ?", (key,))
        row = c.fetchone()
        conn.close()
        
        if row:
            value, updated_at = row
            if time.time() - updated_at < 1800: # 30 menit
                return json.loads(value)
    except Exception as e:
        logger.error(f"[Bullpen Cache] Read error: {e}")
    return None

def save_cached_markets(key, value):
    """Menyimpan data ke cache."""
    try:
        init_cache_db()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO market_cache (key, value, updated_at) VALUES (?, ?, ?)",
                  (key, json.dumps(value), time.time()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"[Bullpen Cache] Save error: {e}")

def parse_game_description(desc):
    """
    Parsing 'June 15 at 10:10PM ET'
    Return: (game_date_et, game_time_et)
    """
    if not desc:
        return None, None
        
    match = re.search(r'(\w+ \d+) at (\d+:\d+(?:AM|PM))\s+ET', desc, re.IGNORECASE)
    if not match:
        return None, None
        
    date_str = match.group(1) # "June 15"
    time_str = match.group(2) # "10:10PM"
    
    # Format: "10:10PM" -> "10:10 PM ET"
    time_formatted = re.sub(r'(AM|PM)', r' \1', time_str, flags=re.IGNORECASE).upper()
    game_time_et = f"{time_formatted} ET"
    
    current_year = datetime.now().year
    try:
        dt = datetime.strptime(f"{date_str} {current_year}", "%B %d %Y")
        game_date_et = dt.strftime("%Y-%m-%d")
        
        return game_date_et, game_time_et
    except Exception as e:
        logger.error(f"[Bullpen Parser] Error parsing desc: {e}")
        return None, None

def get_mlb_ou_markets():
    """
    Mengambil semua game MLB aktif dengan line O/U dari Bullpen CLI.
    Menghitung rentang line (min/max) untuk setiap game.
    """
    cached = get_cached_markets('bullpen_mlb_markets')
    if cached:
        return cached
        
    logger.info("[Bullpen] Mengambil data market harian dari Bullpen CLI...")
    init_cache_db()
    
    et_tz = pytz.timezone('America/New_York')
    today_et_str = datetime.now(et_tz).strftime("%Y-%m-%d")
    
    try:
        cmd = ["bullpen", "polymarket", "discover", "sports", "--sport", "mlb", "--limit", "100", "--output", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.error(f"[Bullpen CLI Error] {result.stderr}")
            return []
            
        data = json.loads(result.stdout)
        events = data.get("events", [])
        
        results = []
        for event in events:
            title = event.get("title", "")
            desc = event.get("description", "")
            
            if " vs. " not in title or "Player Props" in title:
                continue
                
            away_raw, home_raw = title.split(" vs. ", 1)
            away_team = get_official_team_name(away_raw)
            home_team = get_official_team_name(home_raw)
            
            date_et, time_et = parse_game_description(desc)
            if not date_et:
                continue
                
            # Filter Waktu: Skip jika game sudah mulai atau dalam 30 menit (Fix 1)
            try:
                # game_time_et format: "9:40 PM ET" -> "9:40 PM"
                clean_time = time_et.replace(" ET", "").strip()
                game_dt_str = f"{date_et} {clean_time}"
                game_dt = et_tz.localize(datetime.strptime(game_dt_str, "%Y-%m-%d %I:%M %p"))
                
                cutoff_et = datetime.now(et_tz) + timedelta(minutes=30)
                
                if game_dt <= cutoff_et:
                    logger.info(f"[SKIP] {away_team} @ {home_team} sudah dimulai atau dalam 30 menit ({time_et})")
                    continue
            except Exception as e:
                logger.warning(f"[Bullpen Filter] Gagal parse waktu untuk filter: {e}")
                # Jika gagal parse, kita pakai filter tanggal saja sebagai fallback
                if date_et < today_et_str:
                    continue
                
            game_markets = []
            markets = event.get("markets", [])
            for m in markets:
                question = m.get("question", "")
                # Cari market O/U (Exclude F5)
                if "O/U" in question and "1st 5" not in question and "F5" not in question.upper():
                    line_match = re.search(r'O/U (\d+\.?\d*)', question)
                    if not line_match: continue
                    ou_line = float(line_match.group(1))
                    
                    over_price = 0.0
                    under_price = 0.0
                    for out in m.get("outcomes", []):
                        price_val = out.get("price")
                        if price_val is None: price_val = 0.0
                        p = price_val * 100
                        if out["name"] == "Over": over_price = round(p, 1)
                        elif out["name"] == "Under": under_price = round(p, 1)
                    
                    if 1.5 < over_price < 98.5:
                        game_markets.append({
                            'line': ou_line,
                            'over_price': over_price,
                            'under_price': under_price,
                            'market_id': m.get("id")
                        })
            
            if game_markets:
                # Hitung rentang line
                lines = [m['line'] for m in game_markets]
                min_line = min(lines)
                max_line = max(lines)
                line_range = f"{min_line} - {max_line}" if min_line != max_line else f"{min_line}"
                
                # Pilih line utama (paling dekat ke 8.5)
                game_markets.sort(key=lambda x: abs(x['line'] - 8.5))
                best = game_markets[0]
                
                results.append({
                    'away_team': away_team,
                    'home_team': home_team,
                    'ou_line': best['line'],
                    'over_price': best['over_price'],
                    'under_price': best['under_price'],
                    'game_time_et': time_et,
                    'game_date_et': date_et,
                    'line_range': line_range,
                    'market_id': best['market_id'],
                    'source': 'Bullpen CLI'
                })
        
        if results:
            save_cached_markets('bullpen_mlb_markets', results)
        return results
        
    except Exception as e:
        logger.error(f"[Bullpen Error] {e}")
        return []

def get_ou_line(away_team, home_team, game_date_et=None):
    """
    Mengambil line O/U spesifik untuk sebuah matchup.
    """
    markets = get_mlb_ou_markets()
    a_official = get_official_team_name(away_team)
    h_official = get_official_team_name(home_team)
    
    matches = [m for m in markets if m['away_team'] == a_official and m['home_team'] == h_official]
    if game_date_et:
        matches = [m for m in matches if m['game_date_et'] == game_date_et]
        
    if not matches: return None
    
    # Pilih yang harganya paling seimbang
    matches.sort(key=lambda x: abs(x['over_price'] - 50))
    best = matches[0]
    
    return {
        'line': best['ou_line'],
        'over_price': best['over_price'],
        'under_price': best['under_price'],
        'game_time_et': best['game_time_et'],
        'game_date_et': best['game_date_et'],
        'line_range': best['line_range'],
        'market_id': best['market_id'],
        'source': best['source']
    }
