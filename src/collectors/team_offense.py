import requests
from datetime import datetime

MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"

def get_team_season_offense(team_id):
    """
    Mengambil statistik offense tim untuk musim berjalan.
    Metrik: Runs per Game, OPS, K%, BB%, RISP AVG, Batting Average.
    
    Args:
        team_id (int): ID tim MLB.
        
    Returns:
        dict: Dictionary berisi metrik offense utama.
    """
    # Ambil statistik umum
    url_hitting = f"{MLB_API_BASE_URL}/teams/{team_id}/stats?stats=season&group=hitting"
    # Ambil statistik RISP (Runners in Scoring Position)
    url_risp = f"{MLB_API_BASE_URL}/teams/{team_id}/stats?stats=statSplits&group=hitting&sitCodes=risp"
    
    stats = {}
    try:
        # Request hitting stats
        resp_h = requests.get(url_hitting, timeout=10)
        resp_h.raise_for_status()
        data_h = resp_h.json()
        
        if "stats" in data_h and data_h["stats"]:
            s = data_h["stats"][0]["splits"][0]["stat"]
            pa = s.get("plateAppearances", 1)
            games = s.get("gamesPlayed", 1)
            
            stats = {
                "avg": s.get("avg"),
                "ops": s.get("ops"),
                "runs_per_game": round(s.get("runs", 0) / games, 2) if games > 0 else 0,
                "k_pct": round((s.get("strikeOuts", 0) / pa) * 100, 2) if pa > 0 else 0,
                "bb_pct": round((s.get("baseOnBalls", 0) / pa) * 100, 2) if pa > 0 else 0,
            }
            
        # Request RISP stats
        resp_r = requests.get(url_risp, timeout=10)
        if resp_r.status_code == 200:
            data_r = resp_r.json()
            if "stats" in data_r and data_r["stats"]:
                # Cari split yang sitCode-nya 'risp'
                for split in data_r["stats"][0]["splits"]:
                    if split.get("split", {}).get("code") == "risp":
                        stats["risp_avg"] = split["stat"].get("avg")
                        break
                        
        return stats
    except Exception as e:
        print(f"Error get_team_season_offense: {e}")
        return {}

def get_team_last_10_games(team_id):
    """
    Mengambil data performa hitting dalam 10 pertandingan terakhir.
    
    Args:
        team_id (int): ID tim MLB.
        
    Returns:
        list: List berisi statistik per game (batting average, runs, etc).
    """
    # Menggunakan gameLog untuk mengambil histori per pertandingan
    url = f"{MLB_API_BASE_URL}/teams/{team_id}/stats?stats=gameLog&group=hitting"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "stats" in data and data["stats"]:
            # Ambil 10 game terbaru (biasanya urut terbaru di atas)
            return data["stats"][0]["splits"][:10]
        return []
    except Exception as e:
        print(f"Error get_team_last_10_games: {e}")
        return []

def calculate_streak(last_10_games_data):
    """
    Menentukan status streak tim berdasarkan tren Batting Average (BA).
    Logika PRD: 
    - HOT: Rata-rata BA 7 game terakhir > .280
    - COLD: Rata-rata BA 7 game terakhir < .230
    - NEUTRAL: Selain itu.
    
    Args:
        last_10_games_data (list): Output dari get_team_last_10_games.
        
    Returns:
        str: "HOT", "COLD", atau "NEUTRAL".
    """
    if not last_10_games_data or len(last_10_games_data) < 7:
        return "NEUTRAL"
        
    # Ambil 7 game terakhir
    last_7 = last_10_games_data[:7]
    ba_list = []
    
    for game in last_7:
        ba = game["stat"].get("avg")
        try:
            if ba and ba != ".---":
                ba_list.append(float(ba))
        except ValueError:
            continue
            
    if not ba_list:
        return "NEUTRAL"
        
    avg_ba = sum(ba_list) / len(ba_list)
    
    if avg_ba > 0.280:
        return "HOT"
    elif avg_ba < 0.230:
        return "COLD"
    else:
        return "NEUTRAL"

def get_todays_lineup(game_id, team_id):
    """
    Mengambil lineup pemain untuk pertandingan hari ini.
    
    Args:
        game_id (int): ID pertandingan.
        team_id (int): ID tim.
        
    Returns:
        list: List nama pemain dalam urutan batting order.
    """
    url = f"{MLB_API_BASE_URL}/game/{game_id}/boxscore"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        team_type = "home" if data["teams"]["home"]["team"]["id"] == team_id else "away"
        batting_order_ids = data["teams"][team_type].get("battingOrder", [])
        all_players = data["teams"][team_type].get("players", {})
        
        lineup = []
        for p_id in batting_order_ids:
            p_key = f"ID{p_id}"
            if p_key in all_players:
                lineup.append(all_players[p_key]["person"]["fullName"])
                
        return lineup
    except Exception as e:
        print(f"Error get_todays_lineup: {e}")
        return []

if __name__ == "__main__":
    # Test dengan NY Yankees (ID: 147)
    TEST_TEAM_ID = 147
    TEST_GAME_ID = 746048 # Gunakan ID game valid dari schedule
    
    print(f"--- Testing Team Offense for Team ID: {TEST_TEAM_ID} ---")
    
    season_offense = get_team_season_offense(TEST_TEAM_ID)
    print(f"Season Stats: {season_offense}")
    
    last_10 = get_team_last_10_games(TEST_TEAM_ID)
    streak = calculate_streak(last_10)
    print(f"Current Streak Status: {streak}")
    
    print(f"\n--- Testing Lineup for Game {TEST_GAME_ID} ---")
    lineup = get_todays_lineup(TEST_GAME_ID, TEST_TEAM_ID)
    if lineup:
        for i, player in enumerate(lineup, 1):
            print(f"{i}. {player}")
    else:
        print("Lineup belum tersedia atau game ID salah.")
