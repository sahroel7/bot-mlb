import requests
from datetime import datetime, timedelta
import pytz
from src.utils.network import get_request

# URL API MLB Stats (Sport ID 1 adalah MLB)
MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"

def get_todays_games(days_ahead=0):
    """
    Mengambil daftar pertandingan MLB yang dijadwalkan untuk tanggal tertentu (hari ini + days_ahead)
    berdasarkan zona waktu ET (America/New_York).
    
    Returns:
        list: Daftar dictionary berisi info game_id, home_team, away_team, 
              game_time, venue_name, venue_city, dan status.
    """
    # Gunakan zona waktu ET untuk menentukan 'hari ini'
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    
    target_date = (now_et + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
    url = f"{MLB_API_BASE_URL}/schedule?sportId=1&date={target_date}"
    
    try:
        response = get_request(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games_list = []
        
        # Mengecek apakah ada data tanggal dan pertandingan
        if "dates" not in data or not data["dates"]:
            return []
            
        for date_info in data["dates"]:
            for game in date_info.get("games", []):
                status = game.get("status", {}).get("abstractGameState", "")
                
                # Filter: Tolak game yang sudah "Final"
                if status == "Final":
                    continue
                    
                # Ekstraksi data mendasar
                game_data = {
                    "game_id": game.get("gamePk"),
                    "home_team": game.get("teams", {}).get("home", {}).get("team", {}).get("name"),
                    "home_id": game.get("teams", {}).get("home", {}).get("team", {}).get("id"),
                    "away_team": game.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                    "away_id": game.get("teams", {}).get("away", {}).get("team", {}).get("id"),
                    "game_time": game.get("gameDate"),
                    "venue_name": game.get("venue", {}).get("name"),
                    "venue_city": "Unknown",
                    "status": status
                }
                games_list.append(game_data)
                
        return games_list
        
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil jadwal MLB: {e}")
        return []

def get_games_by_et_date(target_date):
    """
    Mengambil daftar pertandingan MLB untuk tanggal ET tertentu (YYYY-MM-DD).
    """
    url = f"{MLB_API_BASE_URL}/schedule?sportId=1&date={target_date}"
    
    try:
        response = get_request(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games_list = []
        if "dates" not in data or not data["dates"]:
            return []
            
        for date_info in data["dates"]:
            for game in date_info.get("games", []):
                status = game.get("status", {}).get("abstractGameState", "")
                if status == "Final":
                    continue
                    
                game_data = {
                    "game_id": game.get("gamePk"),
                    "home_team": game.get("teams", {}).get("home", {}).get("team", {}).get("name"),
                    "home_id": game.get("teams", {}).get("home", {}).get("team", {}).get("id"),
                    "away_team": game.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                    "away_id": game.get("teams", {}).get("away", {}).get("team", {}).get("id"),
                    "game_time": game.get("gameDate"),
                    "venue_name": game.get("venue", {}).get("name"),
                    "venue_city": "Unknown",
                    "status": status
                }
                games_list.append(game_data)
                
        return games_list
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil jadwal MLB untuk {target_date}: {e}")
        return []

def get_upcoming_games():
    """
    Mengambil daftar pertandingan mendatang yang memiliki market O/U aktif di Polymarket.
    Menggunakan Polymarket (Bullpen CLI) sebagai source of truth.
    """
    from src.collectors.bullpen_collector import get_mlb_ou_markets, get_official_team_name
    from src.collectors.polymarket import convert_utc_to_et
    
    # 1. Ambil semua market O/U aktif dari Polymarket
    markets = get_mlb_ou_markets()
    if not markets:
        return []
        
    # 2. Kumpulkan tanggal unik dari market aktif
    dates = {m['game_date_et'] for m in markets if m.get('game_date_et')}
    
    # 3. Ambil jadwal MLB untuk semua tanggal tersebut
    mlb_games = []
    for dt in dates:
        mlb_games.extend(get_games_by_et_date(dt))
        
    # 4. Cocokkan market ke game MLB
    matched_games = []
    for m in markets:
        a_official = get_official_team_name(m['away_team'])
        h_official = get_official_team_name(m['home_team'])
        
        # Cari game yang cocok berdasarkan tim dan tanggal ET
        for g in mlb_games:
            et_date, _ = convert_utc_to_et(g['game_time'])
            
            g_away_official = get_official_team_name(g['away_team'])
            g_home_official = get_official_team_name(g['home_team'])
            
            if (g_away_official == a_official and 
                g_home_official == h_official and 
                et_date == m['game_date_et']):
                
                # Copy and update game data
                game_data = g.copy()
                game_data['game_date_et'] = m['game_date_et']
                matched_games.append(game_data)
                break
                
    return matched_games

def get_todays_games(days_ahead=0):
    """
    Mengambil game MLB dengan market aktif untuk tanggal tertentu (hari ini + days_ahead).
    """
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    target_date = (now_et.date() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
    
    # Ambil semua game mendatang yang ada marketnya
    upcoming = get_upcoming_games()
    
    # Filter berdasarkan target_date
    return [g for g in upcoming if g.get('game_date_et') == target_date]

if __name__ == "__main__":
    # Fungsi test untuk verifikasi output di terminal
    print(f"--- Mengambil Pertandingan MLB Hari Ini ({datetime.now().strftime('%Y-%m-%d')}) ---")
    games = get_todays_games()
    
    if not games:
        print("Tidak ada pertandingan ditemukan atau terjadi kesalahan.")
    else:
        for i, game in enumerate(games, 1):
            print(f"{i}. [{game['game_id']}] {game['away_team']} @ {game['home_team']}")
            print(f"   Waktu: {game['game_time']} | Status: {game['status']}")
            print(f"   Lokasi: {game['venue_name']}")
            print("-" * 30)
