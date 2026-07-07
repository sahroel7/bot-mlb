import requests
from datetime import datetime, timedelta
from src.utils.network import get_request
from src.utils.logger import logger

def parse_ip_to_outs(ip_str: str) -> int:
    """Mengonversi string innings pitched (seperti '1.1', '2.0', '0.2') menjadi total outs."""
    if not ip_str:
        return 0
    try:
        if '.' in ip_str:
            parts = ip_str.split('.')
            innings = int(parts[0])
            fraction = int(parts[1])
            return innings * 3 + fraction
        else:
            return int(ip_str) * 3
    except:
        return 0

def get_bullpen_workload_last_3_days(team_id, game_date_et):
    """
    Mengambil boxscore 2-3 game terakhir tim tersebut via statsapi.mlb.com
    dan menghitung total IP yang dilempar oleh semua reliever di 3 hari terakhir.
    
    Args:
        team_id (int): ID tim MLB.
        game_date_et (str): Tanggal game saat ini (YYYY-MM-DD).
        
    Returns:
        float: Total innings pitched reliever 3 hari terakhir (dalam desimal), atau None jika gagal.
    """
    if not team_id or not game_date_et:
        return None
        
    try:
        # Parse game_date_et
        game_dt = datetime.strptime(game_date_et, "%Y-%m-%d")
        
        # Hitung 3 hari terakhir (game_date_et - 3 sampai game_date_et - 1)
        start_dt = game_dt - timedelta(days=3)
        end_dt = game_dt - timedelta(days=1)
        
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId={team_id}&startDate={start_str}&endDate={end_str}"
        response = get_request(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        game_ids = []
        for date_info in data.get("dates", []):
            for game in date_info.get("games", []):
                status = game.get("status", {}).get("abstractGameState", "")
                if status == "Final":
                    game_ids.append(game.get("gamePk"))
                    
        total_outs = 0
        for g_id in game_ids:
            box_url = f"https://statsapi.mlb.com/api/v1/game/{g_id}/boxscore"
            box_resp = get_request(box_url, timeout=10)
            box_resp.raise_for_status()
            box_data = box_resp.json()
            
            # Cari side home/away
            home_team_id = box_data.get("teams", {}).get("home", {}).get("team", {}).get("id")
            away_team_id = box_data.get("teams", {}).get("away", {}).get("team", {}).get("id")
            
            if home_team_id == team_id:
                side = "home"
            elif away_team_id == team_id:
                side = "away"
            else:
                continue
                
            pitchers_list = box_data.get("teams", {}).get(side, {}).get("pitchers", [])
            if len(pitchers_list) <= 1:
                # Hanya ada 0 atau 1 pitcher, berarti tidak ada reliever yang melempar
                continue
                
            # Pitcher pertama (indeks 0) adalah starter, sisanya reliever
            relievers = pitchers_list[1:]
            players_dict = box_data.get("teams", {}).get(side, {}).get("players", {})
            
            for player_key, player_data in players_dict.items():
                person_id = player_data.get("person", {}).get("id")
                if person_id in relievers:
                    pitching_stats = player_data.get("stats", {}).get("pitching", {})
                    ip_str = pitching_stats.get("inningsPitched")
                    if ip_str:
                        total_outs += parse_ip_to_outs(ip_str)
                        
        return total_outs / 3.0
        
    except Exception as e:
        import traceback
        logger.error(f"[DEBUG BULLPEN WORKLOAD] team_id={team_id} date={game_date_et} | ERROR: {type(e).__name__}: {e}")
        logger.error(f"[DEBUG BULLPEN WORKLOAD] Traceback:\n{traceback.format_exc()}")
        return None
