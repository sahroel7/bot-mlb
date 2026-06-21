import requests
from bs4 import BeautifulSoup
import time
import sqlite3
import os
from datetime import datetime

# Konfigurasi Scraper
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DB_PATH = "data/mlb_bot.db"

def init_db():
    """Memastikan database dan tabel cache tersedia."""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scrape_cache (
            key TEXT PRIMARY KEY,
            value REAL,
            table_name TEXT,
            timestamp DATETIME
        )
    """)
    conn.commit()
    conn.close()

def get_cached_value(key):
    """Mengambil data dari cache jika masih valid (hari yang sama)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT value FROM scrape_cache WHERE key = ? AND date(timestamp) = ?", (key, today))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def cache_value(key, value, table_name):
    """Menyimpan hasil scraping ke cache SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO scrape_cache (key, value, table_name, timestamp)
        VALUES (?, ?, ?, ?)
    """, (key, value, table_name, datetime.now()))
    conn.commit()
    conn.close()

def fetch_with_retry(url, retries=3, delay=2):
    """Melakukan request HTTP dengan retry logic dan delay."""
    headers = {"User-Agent": USER_AGENT}
    for i in range(retries):
        try:
            time.sleep(delay)  # Crawl politeness
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                print(f"Rate limited. Menunggu {delay * 2} detik...")
                time.sleep(delay * 2)
        except Exception as e:
            print(f"Percobaan {i+1} gagal: {e}")
    return None

def get_pitcher_fip(pitcher_name, season_year=2024):
    """
    Mengambil FIP pitcher dari leaderboards FanGraphs.
    """
    cache_key = f"fip_{pitcher_name}_{season_year}"
    cached = get_cached_value(cache_key)
    if cached: return cached

    # URL Leaderboard Pitching (Dasar)
    url = f"https://www.fangraphs.com/leaders.aspx?pos=all&stats=pit&lg=all&qual=0&type=8&season={season_year}&month=0&season1={season_year}&ind=0&team=0&rost=0&age=0&filter=&players=0"
    
    html = fetch_with_retry(url)
    if not html: return None
    
    soup = BeautifulSoup(html, "lxml")
    # Cari table row yang mengandung nama pitcher
    table = soup.find("table", {"class": "rgMasterTable"})
    if not table: return None
    
    for row in table.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) > 1 and pitcher_name.lower() in cols[1].text.lower():
            # Tipe 8 (Standard): FIP biasanya ada di kolom ke-18 (index 17)
            # Catatan: Index kolom bisa berubah tergantung layout FanGraphs
            try:
                fip = float(cols[17].text)
                cache_value(cache_key, fip, "pitching")
                return fip
            except: continue
            
    return None

def get_team_wrc_plus(team_name, season_year=2024):
    """
    Mengambil wRC+ tim dari FanGraphs.
    """
    cache_key = f"wrcplus_{team_name}_{season_year}"
    cached = get_cached_value(cache_key)
    if cached: return cached

    url = f"https://www.fangraphs.com/leaders.aspx?pos=all&stats=bat&lg=all&qual=0&type=8&season={season_year}&month=0&season1={season_year}&ind=0&team=0,ts&rost=0&age=0&filter=&players=0"
    
    html = fetch_with_retry(url)
    if not html: return None
    
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", {"class": "rgMasterTable"})
    if not table: return None
    
    for row in table.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) > 1 and team_name.lower() in cols[1].text.lower():
            try:
                # wRC+ biasanya di kolom terakhir atau dekat situ di Type 8 Dash
                wrc = float(cols[17].text)
                cache_value(cache_key, wrc, "hitting")
                return wrc
            except: continue
    return None

def get_pitcher_ground_ball_rate(pitcher_name, season_year=2024):
    """
    Mengambil GB% (Ground Ball Rate) pitcher dari FanGraphs.
    """
    cache_key = f"gb_pct_{pitcher_name}_{season_year}"
    cached = get_cached_value(cache_key)
    if cached: return cached

    # URL Batted Ball Pitching (Type 2)
    url = f"https://www.fangraphs.com/leaders.aspx?pos=all&stats=pit&lg=all&qual=0&type=2&season={season_year}&month=0&season1={season_year}&ind=0&team=0&rost=0&age=0&filter=&players=0"
    
    html = fetch_with_retry(url)
    if not html: return None
    
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", {"class": "rgMasterTable"})
    if not table: return None
    
    for row in table.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) > 1 and pitcher_name.lower() in cols[1].text.lower():
            try:
                # Kolom ke-8 (index 7) biasanya adalah GB% di Type 2
                gb_text = cols[7].text.strip('%')
                gb_pct = float(gb_text)
                cache_value(cache_key, gb_pct, "pitching")
                return gb_pct
            except: continue
    return None

def get_pitcher_hard_hit_rate(pitcher_name, season_year=2024):
    """
    Mengambil Hard Hit % pitcher dari FanGraphs.
    """
    cache_key = f"hardhit_pct_{pitcher_name}_{season_year}"
    cached = get_cached_value(cache_key)
    if cached: return cached

    # URL Batted Ball Pitching (Type 2) - Hard% biasanya ada di halaman yang sama
    url = f"https://www.fangraphs.com/leaders.aspx?pos=all&stats=pit&lg=all&qual=0&type=2&season={season_year}&month=0&season1={season_year}&ind=0&team=0&rost=0&age=0&filter=&players=0"
    
    html = fetch_with_retry(url)
    if not html: return None
    
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", {"class": "rgMasterTable"})
    if not table: return None
    
    for row in table.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) > 1 and pitcher_name.lower() in cols[1].text.lower():
            try:
                # Kolom ke-14 (index 13) biasanya adalah Hard% di Type 2
                hard_text = cols[13].text.strip('%')
                hard_pct = float(hard_text)
                cache_value(cache_key, hard_pct, "pitching")
                return hard_pct
            except: continue
    return None

# Inisialisasi DB saat modul di-import
init_db()

if __name__ == "__main__":
    print("--- Testing FanGraphs Scraper ---")
    # Contoh: Gerrit Cole (Gunakan nama yang ada di leaderboards)
    fip = get_pitcher_fip("Gerrit Cole")
    print(f"FIP Gerrit Cole: {fip}")
    
    wrc = get_team_wrc_plus("Yankees")
    print(f"wRC+ Yankees: {wrc}")
