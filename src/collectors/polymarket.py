import requests
from datetime import datetime
import time
import os
import pytz
from dotenv import load_dotenv
from src.collectors.bullpen_collector import get_ou_line as get_bullpen_line

load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"

# Global Cache agar tidak berulang kali hit API saat loop banyak game
_MARKETS_CACHE = None
_ODDS_API_CACHE = None
_POLYMARKET_EMPTY_WARNED = False

def convert_utc_to_et(utc_iso_str):
    """Konversi UTC ISO string ke ET Date dan ET Time."""
    try:
        # 2026-06-15T23:10:00Z
        utc_dt = datetime.fromisoformat(utc_iso_str.replace('Z', '+00:00'))
        et_tz = pytz.timezone('America/New_York')
        et_dt = utc_dt.astimezone(et_tz)
        
        game_date = et_dt.strftime("%Y-%m-%d")
        game_time_et = et_dt.strftime("%I:%M %p ET").lstrip('0')
        return game_date, game_time_et
    except:
        return None, "N/A"

# Mapping Nama Tim Polymarket -> MLB API (Jika berbeda)
TEAM_NAME_MAPPING = {
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

def normalize_team_name(name):
    """
    Menormalkan nama tim dari format Polymarket ke format MLB API.
    """
    for short_name, full_name in TEAM_NAME_MAPPING.items():
        if short_name in name:
            return full_name
    return name

def get_mlb_ou_markets():
    """
    Mengambil semua pasar Over/Under MLB yang aktif dari Gamma API.
    
    Returns:
        list: Daftar pasar O/U yang ditemukan.
    """
    global _MARKETS_CACHE, _POLYMARKET_EMPTY_WARNED
    if _MARKETS_CACHE is not None:
        return _MARKETS_CACHE

    # Diperlebar pencariannya karena 'MLB Total' mungkin tidak selalu cocok
    url = f"{GAMMA_API_URL}/markets?active=true&limit=100&search=MLB"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        markets = response.json()
        
        ou_markets = []
        for m in markets:
            title = m.get("title", "").lower()
            q = m.get("question", "").lower()
            # Filter yang mengandung unsur baseball O/U
            if "total runs" in title or "over" in q or "runs" in q:
                ou_markets.append(m)
                
        _MARKETS_CACHE = ou_markets
        
        if not ou_markets and not _POLYMARKET_EMPTY_WARNED:
            print("\n[INFO] Tidak ada market MLB aktif di Polymarket saat ini (Off-season atau belum listing).")
            _POLYMARKET_EMPTY_WARNED = True
            
        return ou_markets
    except Exception as e:
        print(f"Error get_mlb_ou_markets: {e}")
        _MARKETS_CACHE = []
        return []

def get_fallback_odds_api_line(home_team, away_team):
    """
    Fallback menggunakan The Odds API jika Polymarket kosong.
    Membutuhkan ODDS_API_KEY di file .env.
    """
    global _ODDS_API_CACHE
    if not ODDS_API_KEY:
        return None
        
    if _ODDS_API_CACHE is None:
        url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey={ODDS_API_KEY}&regions=us&markets=totals"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                _ODDS_API_CACHE = resp.json()
                print("[INFO] Menggunakan fallback data line dari The Odds API.")
            else:
                _ODDS_API_CACHE = []
        except:
            _ODDS_API_CACHE = []
            
    for game in _ODDS_API_CACHE:
        g_home = game.get("home_team", "")
        g_away = game.get("away_team", "")
        
        # Pencocokan nama tim yang sedikit longgar
        if normalize_team_name(home_team) in g_home or normalize_team_name(g_home) in home_team:
            if normalize_team_name(away_team) in g_away or normalize_team_name(g_away) in away_team:
                bookmakers = game.get("bookmakers", [])
                if bookmakers:
                    markets = bookmakers[0].get("markets", [])
                    for market in markets:
                        if market.get("key") == "totals":
                            outcomes = market.get("outcomes", [])
                            if outcomes:
                                utc_time = game.get("commence_time")
                                game_date_et, game_time_et = convert_utc_to_et(utc_time)
                                
                                return {
                                    "market_id": game.get("id"),
                                    "line": float(outcomes[0].get("point")),
                                    "question": f"The Odds API Fallback: {away_team} @ {home_team}",
                                    "odds": {},
                                    "game_date": game_date_et,
                                    "game_time_et": game_time_et
                                }
    return None

def get_ou_line(home_team, away_team):
    """
    Mencari angka Over/Under line untuk pertandingan tertentu.
    Prioritas: Bullpen CLI -> The Odds API (Fallback)
    """
    # 1. Prioritas Utama: Bullpen CLI
    from src.collectors.bullpen_collector import get_ou_line as get_bullpen_line
    bullpen_data = get_bullpen_line(away_team, home_team)
    if bullpen_data:
        bullpen_data['source'] = 'Bullpen CLI'
        return bullpen_data

    # 2. Fallback: The Odds API
    fallback = get_fallback_odds_api_line(home_team, away_team)
    if fallback:
        fallback['source'] = 'The Odds API (fallback)'
        return fallback

    return None

def get_market_movement(market_id):
    """
    Mengecek pergerakan harga pasar dalam 2 jam terakhir.
    (Sangat berguna untuk mendeteksi sinyal 'Sharp Money').
    
    Returns:
        float: Selisih harga (positive = naik, negative = turun).
    """
    # Implementasi ini memerlukan akses ke history API atau menyimpan data lokal
    # Untuk MVP, kita return 0 atau placeholder
    return 0.0

if __name__ == "__main__":
    print("--- Mencari Pasar MLB Over/Under di Polymarket ---")
    markets = get_mlb_ou_markets()
    
    if not markets:
        print("Tidak ada pasar aktif ditemukan.")
    else:
        for m in markets:
            print(f"ID: {m['id']} | {m['question']}")
            print("-" * 50)
