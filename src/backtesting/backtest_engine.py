"""
Modul Backtesting (Phase 3 Intelligence).
Menjalankan simulasi prediksi terhadap data pertandingan masa lalu untuk mengukur akurasi bot.
"""

import requests
import sqlite3
import os
import sys
from datetime import datetime, timedelta
import time
from colorama import Fore, Style, init

# Fix Python path for direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Core Processors
from src.processors.run_calculator import calculate_expected_total_runs, make_recommendation, calculate_confidence
from src.data.park_factors import get_park_factor, classify_park

init(autoreset=True)
DB_PATH = "data/mlb_bot.db"
MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"

def init_backtest_db():
    """Membuat tabel untuk menyimpan hasil backtest."""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            game_id INTEGER PRIMARY KEY,
            date TEXT,
            home_team TEXT,
            away_team TEXT,
            actual_runs REAL,
            polymarket_line_sim REAL,
            bot_expected_runs REAL,
            recommendation TEXT,
            confidence TEXT,
            is_correct INTEGER,
            park_type TEXT,
            weather_condition TEXT
        )
    """)
    conn.commit()
    conn.close()

def fetch_historical_games(start_date, end_date):
    """
    Mengambil data pertandingan masa lalu yang sudah selesai (Status: Final).
    
    Args:
        start_date (str): Format YYYY-MM-DD
        end_date (str): Format YYYY-MM-DD
    """
    print(f"Mengambil data historis dari {start_date} hingga {end_date}...")
    url = f"{MLB_API_BASE_URL}/schedule?sportId=1&startDate={start_date}&endDate={end_date}"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        games_list = []
        if "dates" not in data:
            return []
            
        for date_info in data["dates"]:
            for game in date_info.get("games", []):
                # Hanya ambil game yang sudah selesai
                if game.get("status", {}).get("statusCode") == "F":
                    home_score = game.get("teams", {}).get("home", {}).get("score", 0)
                    away_score = game.get("teams", {}).get("away", {}).get("score", 0)
                    total_runs = home_score + away_score
                    
                    games_list.append({
                        "game_id": game.get("gamePk"),
                        "date": game.get("gameDate")[:10],
                        "home_team": game.get("teams", {}).get("home", {}).get("team", {}).get("name"),
                        "home_team_id": game.get("teams", {}).get("home", {}).get("team", {}).get("id"),
                        "away_team": game.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                        "away_team_id": game.get("teams", {}).get("away", {}).get("team", {}).get("id"),
                        "actual_runs": total_runs,
                        "venue_name": game.get("venue", {}).get("name")
                    })
        return games_list
    except Exception as e:
        print(f"Error fetching historical games: {e}")
        return []

def run_backtest(start_date, end_date):
    """
    Menjalankan simulasi backtest penuh untuk rentang tanggal tertentu.
    """
    init_backtest_db()
    games = fetch_historical_games(start_date, end_date)
    
    if not games:
        print("Tidak ada data pertandingan historis yang ditemukan.")
        return

    print(f"Memulai backtest untuk {len(games)} pertandingan...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    correct_predictions = 0
    total_predictions = 0

    for idx, game in enumerate(games, 1):
        print(f"[{idx}/{len(games)}] Backtesting {game['away_team']} @ {game['home_team']}...", end="\r")
        
        # 1. Simulasi Polymarket Line 
        # Karena sulit mendapat historical Polymarket line, kita gunakan baseline 8.5 
        # atau gunakan actual_runs dengan sedikit noise untuk mensimulasikan market efisien.
        # Untuk tujuan pengujian AI murni, kita pakai statis 8.5 atau rata-rata liga
        simulated_line = 8.5 
        
        # 2. Setup Data (Untuk backtest idealnya ambil data SEBELUM game dimulai, 
        # tapi untuk MVP kita gunakan baseline statistik sederhana)
        # Note: Pengambilan data historis akurat per tanggal sangat berat via API gratis, 
        # jadi kita dummy-kan beberapa metrik untuk keperluan arsitektur.
        park_factor = get_park_factor(game['home_team_id'])
        
        game_mock_data = {
            "home_team_id": game['home_team_id'],
            "home_team_stats": {"runs_per_game": 4.5, "team_era": 4.2},
            "away_team_stats": {"runs_per_game": 4.5, "team_era": 4.2},
            "home_pitcher_stats": {"era": 4.0, "whip": 1.3},
            "away_pitcher_stats": {"era": 4.0, "whip": 1.3},
            "home_pitcher_last_3": [],
            "away_pitcher_last_3": [],
            "home_bullpen_era": 4.0,
            "away_bullpen_era": 4.0,
            "home_streak": "NEUTRAL",
            "away_streak": "NEUTRAL",
            "weather": {"temperature_fahrenheit": 75, "wind_speed_mph": 5, "wind_direction_degrees": 0, "stadium_orientation": 45},
            "park_factor": park_factor
        }
        
        # 3. Kalkulasi Bot
        analysis = calculate_expected_total_runs(game_mock_data)
        rec = make_recommendation(analysis["final_expected_runs"], simulated_line)
        conf = calculate_confidence(analysis["final_expected_runs"], simulated_line)
        
        # 4. Evaluasi Hasil (Hanya hitung jika bot memberikan rekomendasi)
        is_correct = None
        if "SKIP" not in rec:
            total_predictions += 1
            if ("OVER" in rec and game['actual_runs'] > simulated_line) or \
               ("UNDER" in rec and game['actual_runs'] < simulated_line):
                is_correct = 1
                correct_predictions += 1
            else:
                is_correct = 0

        # 5. Simpan ke Database
        cursor.execute("""
            INSERT OR REPLACE INTO backtest_results 
            (game_id, date, home_team, away_team, actual_runs, polymarket_line_sim, 
             bot_expected_runs, recommendation, confidence, is_correct, park_type, weather_condition)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game['game_id'], game['date'], game['home_team'], game['away_team'], 
            game['actual_runs'], simulated_line, analysis["final_expected_runs"],
            rec, conf, is_correct, classify_park(park_factor), "NORMAL"
        ))
        
        # Crawl politeness
        time.sleep(0.1)

    conn.commit()
    conn.close()
    print("\nBacktest selesai! Data disimpan ke database.")

def generate_backtest_report():
    """Membaca database dan menghasilkan laporan performa bot."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + Fore.CYAN + Style.BRIGHT + "📊 LAPORAN BACKTEST PHASE 3 📊" + "\n")
    
    # Keseluruhan
    cursor.execute("SELECT COUNT(*), SUM(is_correct) FROM backtest_results WHERE is_correct IS NOT NULL")
    total_bets, correct_bets = cursor.fetchone()
    
    if total_bets == 0:
        print("Belum ada data backtest yang memiliki rekomendasi OVER/UNDER.")
        return
        
    win_rate = (correct_bets / total_bets) * 100
    color = Fore.GREEN if win_rate > 52.0 else Fore.RED
    print(f"Total Prediksi  : {total_bets} game")
    print(f"Prediksi Benar  : {correct_bets} game")
    print(f"Win Rate        : {color}{win_rate:.2f}% {Style.RESET_ALL}(Target PRD: > 52%)")
    
    # Berdasarkan Confidence
    print(f"\n{Style.BRIGHT}--- Win Rate Berdasarkan Confidence ---")
    for level in ["HIGH 🔥", "MEDIUM ⚡"]:
        cursor.execute("SELECT COUNT(*), SUM(is_correct) FROM backtest_results WHERE confidence = ? AND is_correct IS NOT NULL", (level,))
        t, c = cursor.fetchone()
        if t > 0:
            print(f"{level[:4]:<6}: {(c/t)*100:.2f}% ({c}/{t})")
            
    # Berdasarkan Park Type
    print(f"\n{Style.BRIGHT}--- Win Rate Berdasarkan Tipe Stadion ---")
    for p_type in ["HITTERS_PARK", "PITCHERS_PARK", "NEUTRAL"]:
        cursor.execute("SELECT COUNT(*), SUM(is_correct) FROM backtest_results WHERE park_type = ? AND is_correct IS NOT NULL", (p_type,))
        t, c = cursor.fetchone()
        if t > 0:
            print(f"{p_type:<15}: {(c/t)*100:.2f}% ({c}/{t})")

    conn.close()

if __name__ == "__main__":
    # Test jalankan backtest untuk 3 hari ke belakang (MVP)
    # Jangan terlalu lama agar tidak diblock API
    end_dt = datetime.now() - timedelta(days=1)
    start_dt = end_dt - timedelta(days=3)
    
    s_date = start_dt.strftime("%Y-%m-%d")
    e_date = end_dt.strftime("%Y-%m-%d")
    
    run_backtest(s_date, e_date)
    generate_backtest_report()
