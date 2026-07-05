import requests
from datetime import datetime
from src.utils.network import get_request

MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"

def get_starting_pitchers(game_id):
    """
    Mengambil ID dan nama starting pitcher untuk tim home dan away.
    
    Args:
        game_id (int): ID pertandingan MLB.
        
    Returns:
        dict: Berisi 'home' dan 'away' pitcher info (id dan name).
    """
    # Hydrate probablePitcher untuk mendapatkan data starter sebelum game dimulai
    url = f"{MLB_API_BASE_URL}/schedule?gamePk={game_id}&hydrate=probablePitcher"
    
    try:
        response = get_request(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        pitchers = {"home": None, "away": None}
        
        if "dates" in data and data["dates"]:
            game = data["dates"][0]["games"][0]
            teams = game.get("teams", {})
            
            for side in ["home", "away"]:
                p_data = teams.get(side, {}).get("probablePitcher", {})
                if p_data:
                    pitchers[side] = {
                        "id": p_data.get("id"),
                        "name": p_data.get("fullName")
                    }
        return pitchers
    except Exception as e:
        print(f"Error get_starting_pitchers: {e}")
        return {"home": None, "away": None}

def get_pitcher_season_stats(pitcher_id):
    """
    Mengambil statistik musim berjalan untuk seorang pitcher.
    Metrik: ERA, WHIP, K/9, BB/9, HR/9, IP per start.
    
    Args:
        pitcher_id (int): ID unik pemain.
        
    Returns:
        dict: Dictionary berisi metrik statistik utama.
    """
    if not pitcher_id:
        return {}
        
    url = f"{MLB_API_BASE_URL}/people/{pitcher_id}/stats?stats=statsSingleSeason&group=pitching"
    
    try:
        response = get_request(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        stats = {}
        if "stats" in data and data["stats"]:
            season_stats = data["stats"][0]["splits"][0]["stat"]
            
            # Ekstraksi metrik sesuai PRD
            stats = {
                "era": season_stats.get("era"),
                "whip": season_stats.get("whip"),
                "k9": season_stats.get("strikeoutsPer9Inn"),
                "bb9": season_stats.get("walksPer9Inn"),
                "hr9": season_stats.get("homeRunsPer9"),
                "games_started": season_stats.get("gamesStarted"),
                "innings_pitched": season_stats.get("inningsPitched"),
            }
            
            # Hitung rata-rata IP per start
            if stats["games_started"] and stats["games_started"] > 0:
                stats["ip_per_start"] = round(float(stats["innings_pitched"]) / stats["games_started"], 2)
            else:
                stats["ip_per_start"] = 0
                
        return stats
    except Exception as e:
        print(f"Error get_pitcher_season_stats: {e}")
        return {}

def get_pitcher_last_3_starts(pitcher_id):
    """
    Mengambil data performa dalam 3 pertandingan terakhir.
    Digunakan untuk analisis kelelahan dan tren terkini.
    
    Args:
        pitcher_id (int): ID unik pemain.
        
    Returns:
        list: List berisi data 3 game terakhir (pitch count, IP, date).
    """
    if not pitcher_id:
        return []
        
    url = f"{MLB_API_BASE_URL}/people/{pitcher_id}/stats?stats=gameLog&group=pitching"
    
    try:
        response = get_request(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        last_3 = []
        if "stats" in data and data["stats"]:
            # splits dikembalikan secara kronologis (dari awal musim ke terbaru).
            # Ambil 3 split terakhir (pertandingan terbaru) dan balik urutannya (terbaru ke terlama).
            recent_splits = data["stats"][0]["splits"][-3:]
            recent_splits.reverse()
            logs = recent_splits
            
            for log in logs:
                stat = log["stat"]
                last_3.append({
                    "date": log.get("date"),
                    "pitch_count": stat.get("numberOfPitches"),
                    "innings_pitched": stat.get("inningsPitched"),
                    "strikeouts": stat.get("strikeOuts")
                })
        return last_3
    except Exception as e:
        print(f"Error get_pitcher_last_3_starts: {e}")
        return []

def get_bullpen_era(team_id):
    """
    Mengambil rata-rata ERA bullpen tim. 
    Menggunakan filter 'relief' pitching stats.
    
    Args:
        team_id (int): ID tim MLB.
        
    Returns:
        float: Nilai ERA bullpen.
    """
    # Mengambil stats team relief pitching (RP) secara spesifik dengan parameter pitchingRole
    url = f"{MLB_API_BASE_URL}/teams/{team_id}/stats?stats=season&group=pitching&pitchingRole=RP"
    
    try:
        response = get_request(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "stats" in data and data["stats"]:
            team_stats = data["stats"][0]["splits"][0]["stat"]
            return team_stats.get("era")
        return None
    except Exception as e:
        print(f"Error get_bullpen_era: {e}")
        return None

if __name__ == "__main__":
    # Test dengan ID Pertandingan nyata (Contoh: 746048 - NYY vs BOS jika tersedia)
    # Anda bisa mengganti ID ini dengan ID dari get_todays_games()
    TEST_GAME_ID = 746048 
    
    print(f"--- Testing Pitcher Stats for Game ID: {TEST_GAME_ID} ---")
    
    pitchers = get_starting_pitchers(TEST_GAME_ID)
    print(f"Starters: {pitchers}")
    
    for side, info in pitchers.items():
        if info:
            print(f"\nAnalisis {side.upper()} Pitcher: {info['name']}")
            stats = get_pitcher_season_stats(info['id'])
            print(f"Season Stats: {stats}")
            
            recent = get_pitcher_last_3_starts(info['id'])
            print(f"Last 3 Starts: {recent}")
            
    # Test Bullpen (ID 147 = Yankees sebagai contoh)
    print(f"\nBullpen ERA Team 147: {get_bullpen_era(147)}")
