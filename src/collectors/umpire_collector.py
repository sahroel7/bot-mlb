import requests
from src.utils.network import get_request

def get_home_plate_umpire(game_id):
    """
    Mengambil nama home plate umpire untuk game_id dari statsapi.mlb.com.
    
    Args:
        game_id (str/int): ID pertandingan MLB.
        
    Returns:
        str: Nama umpire, atau None jika tidak ditemukan/gagal.
    """
    if not game_id:
        return None
    try:
        url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"
        response = get_request(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        officials = data.get("officials", [])
        for official in officials:
            if official.get("officialType") == "Home Plate":
                umpire_name = official.get("official", {}).get("fullName")
                if umpire_name:
                    return umpire_name
        return None
    except Exception as e:
        return None
