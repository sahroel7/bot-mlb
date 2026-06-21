"""
File Simulasi Bot MLB AI.
Menguji 3 skenario (OVER, UNDER, SKIP) dengan data hardcoded sesuai PRD.
"""

import sys
import os

# Menambahkan direktori root proyek ke sys.path agar 'src' bisa diimport
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.processors.run_calculator import calculate_expected_total_runs, make_recommendation, calculate_confidence
from src.output.terminal_formatter import format_game_analysis
from src.output.telegram_sender import send_daily_summary
from src.scheduler.alert_system import send_high_confidence_alert
from src.database.prediction_tracker import save_prediction
from colorama import init

init(autoreset=True)

def run_simulations():
    print("━" * 60)
    print("  🚀 MENJALANKAN SIMULASI MLB AI BOT (DATA HARDCODED) 🚀  ")
    print("━" * 60 + "\n")

    # --- SCENARIO 1: CLEAR OVER ---
    # High scoring environment: Coors, Heat, Wind Out, Weak Pitchers, Hot Offense
    game1_info = {
        "away_team": "NY Yankees",
        "home_team": "Colorado Rockies",
        "game_time": "2026-06-13T20:10:00Z",
        "venue_name": "Coors Field",
        "polymarket_line": 9.0
    }
    game1_data = {
        "home_team_id": 115, # Rockies
        "home_team_stats": {"runs_per_game": 5.2, "team_era": 5.5, "ops": 0.810, "risp_avg": 0.290},
        "away_team_stats": {"runs_per_game": 4.9, "team_era": 4.1, "ops": 0.790, "risp_avg": 0.270},
        "home_pitcher_stats": {"era": 5.4, "whip": 1.5, "k9": 6.5, "hr9": 1.7},
        "away_pitcher_stats": {"era": 4.8, "whip": 1.4, "k9": 7.2, "hr9": 1.4},
        "home_pitcher_last_3": [{"pitch_count": 105, "innings_pitched": 4.2}, {"pitch_count": 102, "innings_pitched": 5.0}], # Fatigue
        "away_pitcher_last_3": [],
        "home_bullpen_era": 5.1,
        "away_bullpen_era": 4.4,
        "home_streak": "HOT",
        "away_streak": "HOT",
        "weather": {
            "temperature_fahrenheit": 88,
            "wind_speed_mph": 20,
            "wind_direction_degrees": 225, # OUTWARD for orientation 45
            "stadium_orientation": 45,
            "humidity_percent": 30,
            "precipitation_probability": 0
        },
        "park_factor": 113 # Coors Field
    }

    # --- SCENARIO 2: CLEAR UNDER ---
    # Pitcher duel: Oracle Park, Cold, Wind In, Elite Aces, Cold Offense
    game2_info = {
        "game_id": "sim_game_2",
        "away_team": "SD Padres",
        "home_team": "SF Giants",
        "game_time": "2026-06-13T21:45:00Z",
        "venue_name": "Oracle Park",
        "polymarket_line": 7.5
    }
    game2_data = {
        "home_team_id": 137, # Giants
        "home_team_stats": {"runs_per_game": 3.8, "team_era": 3.6, "ops": 0.680, "risp_avg": 0.210},
        "away_team_stats": {"runs_per_game": 4.0, "team_era": 3.4, "ops": 0.710, "risp_avg": 0.220},
        "home_pitcher_stats": {"era": 2.8, "fip": 2.6, "whip": 0.98, "k9": 11.2, "hr9": 0.6},
        "away_pitcher_stats": {"era": 2.4, "fip": 2.3, "whip": 0.92, "k9": 11.8, "hr9": 0.5},
        "home_pitcher_last_3": [],
        "away_pitcher_last_3": [],
        "home_bullpen_era": 3.1,
        "away_bullpen_era": 2.9,
        "home_streak": "COLD",
        "away_streak": "NEUTRAL",
        "weather": {
            "temperature_fahrenheit": 58,
            "wind_speed_mph": 15,
            "wind_direction_degrees": 45, # INWARD for orientation 67 (close enough)
            "stadium_orientation": 67,
            "humidity_percent": 65,
            "precipitation_probability": 0
        },
        "park_factor": 93 # Oracle Park
    }

    # --- SCENARIO 3: SKIP ---
    # Mixed signals or near-line
    game3_info = {
        "game_id": "sim_game_3",
        "away_team": "LA Dodgers",
        "home_team": "NY Mets",
        "game_time": "2026-06-13T19:10:00Z",
        "venue_name": "Citi Field",
        "polymarket_line": 8.5
    }
    game3_data = {
        "home_team_id": 121, # Mets
        "home_team_stats": {"runs_per_game": 4.5, "team_era": 4.0, "ops": 0.750, "risp_avg": 0.250},
        "away_team_stats": {"runs_per_game": 4.6, "team_era": 3.8, "ops": 0.760, "risp_avg": 0.255},
        "home_pitcher_stats": {"era": 3.8, "whip": 1.25, "k9": 8.5},
        "away_pitcher_stats": {"era": 4.0, "whip": 1.30, "k9": 8.2},
        "home_pitcher_last_3": [],
        "away_pitcher_last_3": [],
        "home_bullpen_era": 4.0,
        "away_bullpen_era": 3.9,
        "home_streak": "NEUTRAL",
        "away_streak": "NEUTRAL",
        "weather": {
            "temperature_fahrenheit": 72,
            "wind_speed_mph": 5,
            "wind_direction_degrees": 0,
            "stadium_orientation": 45,
            "humidity_percent": 50,
            "precipitation_probability": 0
        },
        "park_factor": 95 # Citi Field
    }

    scenarios = [
        (game1_info, game1_data, "SCENARIO 1: CLEAR OVER"),
        (game2_info, game2_data, "SCENARIO 2: CLEAR UNDER"),
        (game3_info, game3_data, "SCENARIO 3: SKIP")
    ]

    all_analyses = []

    for info, data, title in scenarios:
        print(f"\n--- {title} ---")
        analysis = calculate_expected_total_runs(data)
        analysis["recommendation"] = make_recommendation(analysis["final_expected_runs"], info['polymarket_line'])
        analysis["confidence"] = calculate_confidence(analysis["final_expected_runs"], info['polymarket_line'])
        
        output = format_game_analysis(info, analysis)
        print(output)
        
        # Simpan ke DB untuk testing real-time tracking
        info['raw_stats'] = data
        save_prediction(info, analysis)
        
        # Test mengirim Telegram Alert (Hanya akan terkirim jika MEDIUM/HIGH sesuai filter di telegram_sender)
        send_high_confidence_alert(info, analysis)
        
        all_analyses.append({
            "game_info": info,
            "analysis": analysis
        })
        
    print("\n--- MENGIRIM DAILY SUMMARY KE TELEGRAM ---")
    send_daily_summary(all_analyses)
    print("✅ Simulasi Selesai.")

if __name__ == "__main__":
    run_simulations()
