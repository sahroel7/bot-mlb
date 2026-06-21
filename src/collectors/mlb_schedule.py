import requests
from datetime import datetime, timedelta
import pytz

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
        response = requests.get(url, timeout=10)
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

def get_upcoming_games():
    """Mengambil game hari ini dan besok."""
    games_today = get_todays_games(days_ahead=0)
    games_tomorrow = get_todays_games(days_ahead=1)
    
    # Gabungkan dan hapus duplikat jika ada (berdasarkan game_id)
    all_games = {g['game_id']: g for g in games_today + games_tomorrow}
    return list(all_games.values())

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
