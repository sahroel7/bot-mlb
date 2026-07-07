import argparse
import time
import sys
import re
import pytz
from datetime import datetime, timedelta
from colorama import Fore, Style, init

from src.utils.logger import logger
from src.utils.health_check import run_health_check

# Import Collectors
from src.collectors.mlb_schedule import get_upcoming_games, get_todays_games
from src.collectors.polymarket import get_ou_line
from src.collectors.pitcher_stats import (
    get_starting_pitchers, get_pitcher_season_stats, 
    get_pitcher_last_3_starts, get_bullpen_era
)
from src.collectors.team_offense import (
    get_team_season_offense, get_team_last_10_games, calculate_streak
)
from src.collectors.weather import get_game_weather
from src.collectors.bullpen_workload_collector import get_bullpen_workload_last_3_days

# Import Data & Processors
from src.data.park_factors import get_park_factor
from src.processors.run_calculator import (
    calculate_expected_total_runs, make_recommendation, calculate_confidence
)
from src.output.terminal_formatter import (
    format_game_analysis, format_daily_summary, format_no_data_warning
)
from src.output.telegram_sender import send_daily_summary
from src.scheduler.alert_system import send_high_confidence_alert

# Import DB
from src.database.db_setup import initialize_database, get_db_connection
from src.database.prediction_tracker import save_prediction, log_experiment_prediction
from src.database.result_fetcher import process_yesterdays_results
from src.experiments.versions import PRODUCTION_VERSION, EXPERIMENT_VERSIONS

# Inisialisasi Colorama
init(autoreset=True)

def generate_game_id(away_team, home_team, game_date_et, game_time_et):
    """
    Menghasilkan ID unik dan robust berdasarkan nama tim, tanggal, dan jam (ET).
    Penting untuk mengatasi bug duplikasi pada doubleheader.
    Format: AWAY_HOME_YYYY-MM-DD_HHMM(AM/PM)
    Contoh: MAR_PHI_2026-06-18_0540AM
    """
    # Ambil 3 huruf pertama nama tim dari bagian akhir nama
    # misal 'Miami Marlins' -> 'MAR', 'Chicago White Sox' -> 'SOX' (atau WHI, pokoknya konsisten)
    away_code = away_team.split()[-1][:3].upper()
    home_code = home_team.split()[-1][:3].upper()
    
    # Bersihkan string waktu (hanya angka dan AM/PM)
    time_clean = re.sub(r'[^0-9APM]', '', game_time_et.upper())
    
    return f"{away_code}_{home_code}_{game_date_et}_{time_clean}"

def is_game_upcoming(game_time_et, game_date_et, buffer_minutes=30):
    """
    Mengecek apakah game masih akan datang (belum dimulai).
    Memberikan buffer 30 menit sebelum first pitch.
    """
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    
    try:
        # Bersihkan " ET" jika ada
        clean_time = game_time_et.replace(" ET", "").strip()
        game_dt_str = f"{game_date_et} {clean_time}"
        game_dt = et_tz.localize(datetime.strptime(game_dt_str, "%Y-%m-%d %I:%M %p"))
        
        cutoff = now_et + timedelta(minutes=buffer_minutes)
        return game_dt > cutoff
    except Exception as e:
        logger.warning(f"[Safety Net] Tidak bisa parse waktu {game_date_et} {game_time_et}: {e}")
        return True  # Default: biarkan analisis jika ragu

def print_banner():
    """Menampilkan banner selamat datang bot."""
    today = datetime.now().strftime("%d %B %Y")
    print(Fore.CYAN + Style.BRIGHT + "━" * 60)
    print(Fore.WHITE + Style.BRIGHT + "  ⚾ MLB POLYMARKET OVER/UNDER PREDICTION AI BOT ⚾  ")
    print(Fore.CYAN + "  Status: Phase 1 MVP | Hari Ini: " + Fore.YELLOW + today)
    print(Fore.CYAN + Style.BRIGHT + "━" * 60 + "\n")

def run_analysis(args):
    """Fungsi utama untuk menjalankan alur analisis."""
    print_banner()
    
    # Jalankan Health Check sebelum memulai apapun
    if not run_health_check():
        logger.critical("Health Check gagal. Menghentikan bot.")
        sys.exit(1)
        
    # 0. Setup Database dan Update Hasil Kemarin
    try:
        initialize_database()
        logger.info(f"{Fore.BLUE}[0/4] Memproses hasil pertandingan kemarin...")
        process_yesterdays_results()
        
        # Ambil ringkasan kemarin untuk ditampilkan
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        conn = get_db_connection()
        perf_row = conn.execute("SELECT total_correct, total_predictions_made, win_rate_daily FROM daily_performance WHERE date = ?", (yesterday_str,)).fetchone()
        conn.close()
        
        if perf_row and perf_row['total_predictions_made'] and perf_row['total_predictions_made'] > 0:
            logger.info(f"{Fore.CYAN}  📊 Hasil kemarin: {perf_row['total_correct']}/{perf_row['total_predictions_made']} prediksi benar ({perf_row['win_rate_daily']:.1f}%)\n")
        else:
            logger.info(f"{Fore.CYAN}  📊 Tidak ada prediksi kemarin untuk diupdate\n")
    except Exception as e:
        logger.warning(f"{Fore.YELLOW}  ⚠️ [WARNING] Gagal inisialisasi DB atau update hasil: {e}\n")
    
    # 1. Ambil Jadwal
    logger.info(f"{Fore.BLUE}[1/4] Mengambil jadwal pertandingan MLB...")
    if hasattr(args, 'days') and args.days is not None:
        games = get_todays_games(days_ahead=args.days)
    else:
        games = get_upcoming_games()
        
    if not games:
        logger.error(Fore.RED + "Tidak ada pertandingan ditemukan.")
        return

    # Filter jika ada argumen --game (mencari berdasarkan ID)
    if hasattr(args, 'game') and args.game:
        games = [g for g in games if str(g['game_id']) == args.game]
        if not games:
            logger.error(Fore.RED + f"Game ID {args.game} tidak ditemukan di jadwal hari ini.")
            return

    logger.info(f"{Fore.GREEN}Ditemukan {len(games)} pertandingan.\n")
    
    all_analyses = []
    waiting_games = []

    # 2. Proses Setiap Game
    logger.info(f"{Fore.BLUE}[2/4] Menganalisis pasar Polymarket & Statistik...")
    for idx, game in enumerate(games, 1):
        try:
            home_team = game['home_team']
            away_team = game['away_team']
            mlb_api_game_id = game['game_id']
            
            logger.info(f"{Fore.YELLOW}  ({idx}/{len(games)}) Menganalisis: {away_team} @ {home_team}...")
            
            # a. Cari Line Polymarket (atau Fallback)
            market_info = get_ou_line(home_team, away_team, game.get('game_date_et'))
            if not market_info:
                logger.warning(f"{Fore.BLACK}{Style.BRIGHT}  [WAITING] {away_team} @ {home_team}: Tidak ada odds yang tersedia.")
                
                # Simpan ke waiting_markets
                try:
                    conn = get_db_connection()
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn.execute("""
                        INSERT OR IGNORE INTO waiting_markets 
                        (game_id, game_date, away_team, home_team, first_checked_at, last_checked_at, status)
                        VALUES (?, ?, ?, ?, ?, ?, 'pending')
                    """, (str(mlb_api_game_id), game['game_time'][:10], away_team, home_team, now_str, now_str))
                    conn.commit()
                    conn.close()
                except Exception as db_err:
                    logger.warning(f"  ⚠️ Gagal simpan ke waiting_markets: {db_err}")
                
                waiting_games.append(game)
                continue
            
            # Safety Net: Skip jika game sudah lewat atau terlalu dekat (Fix 2)
            if not is_game_upcoming(market_info.get('game_time_et', 'N/A'), market_info.get('game_date_et', '')):
                logger.info(f"{Fore.BLACK}{Style.BRIGHT}  [SKIP] {away_team} @ {home_team} sudah dimulai atau dalam 30 menit.")
                continue

            # Rate limiting sederhana antar request API
            time.sleep(1)

            # b. Collect Data Pitcher
            pitchers = get_starting_pitchers(mlb_api_game_id)
            home_pitcher_id = pitchers['home']['id'] if pitchers['home'] else None
            away_pitcher_id = pitchers['away']['id'] if pitchers['away'] else None
            
            # c. Collect Semua Statistik (Pitcher, Offense, Weather)
            # Mengumpulkan ke dalam satu objek besar untuk processor
            home_last_10 = get_team_last_10_games(game.get('home_id'))
            away_last_10 = get_team_last_10_games(game.get('away_id'))
            
            game_date = game.get('game_date_et') or market_info.get('game_date_et') or (game['game_time'][:10] if game.get('game_time') else datetime.now().strftime('%Y-%m-%d'))
            
            home_workload = None
            away_workload = None
            try:
                home_workload = get_bullpen_workload_last_3_days(game.get('home_id'), game_date)
            except Exception as e:
                logger.warning(f"  ⚠️ Gagal mengambil workload bullpen home: {e}")
                
            try:
                away_workload = get_bullpen_workload_last_3_days(game.get('away_id'), game_date)
            except Exception as e:
                logger.warning(f"  ⚠️ Gagal mengambil workload bullpen away: {e}")
            
            game_full_data = {
                "game_id": mlb_api_game_id,
                "home_team_id": game.get('home_id'),
                "away_team_id": game.get('away_id'),
                "home_team_stats": get_team_season_offense(game.get('home_id')),
                "away_team_stats": get_team_season_offense(game.get('away_id')),
                "home_pitcher_stats": get_pitcher_season_stats(home_pitcher_id),
                "away_pitcher_stats": get_pitcher_season_stats(away_pitcher_id),
                "home_pitcher_last_3": get_pitcher_last_3_starts(home_pitcher_id),
                "away_pitcher_last_3": get_pitcher_last_3_starts(away_pitcher_id),
                "home_bullpen_era": get_bullpen_era(game.get('home_id')),
                "away_bullpen_era": get_bullpen_era(game.get('away_id')),
                "home_streak": calculate_streak(home_last_10),
                "away_streak": calculate_streak(away_last_10),
                "home_last_10_raw": home_last_10,
                "away_last_10_raw": away_last_10,
                "weather": get_game_weather(game['venue_name'], game['game_time']),
                "park_factor": get_park_factor(game.get('home_id')),
                "home_bullpen_workload_3d": home_workload,
                "away_bullpen_workload_3d": away_workload
            }
            
            # d. Kalkulasi Expected Runs
            analysis = calculate_expected_total_runs(game_full_data)
            
            # e. Tambahkan Hasil Rekomendasi
            analysis["recommendation"] = make_recommendation(analysis["final_expected_runs"], market_info['line'], volatility_score=analysis['volatility_score'])
            analysis["confidence"] = calculate_confidence(analysis["final_expected_runs"], market_info['line'])
            
            # Pass layer type if exists
            if hasattr(args, 'layer') and args.layer:
                analysis['layer_type'] = args.layer
            
            # f. Tampilkan Output Detail Jika Tidak Silent
            game_info = game
            game_info['polymarket_line'] = market_info['line']
            game_info['odds_source'] = market_info.get('source', 'Unknown')
            game_info['game_time_et'] = market_info.get('game_time_et', 'N/A')
            game_info['game_date_et'] = market_info.get('game_date_et')
            game_info['line_range'] = market_info.get('line_range', '-')
            game_info['home_pitcher'] = pitchers['home']['name'] if (pitchers.get('home') and isinstance(pitchers['home'], dict) and pitchers['home'].get('name')) else 'Unknown'
            game_info['away_pitcher'] = pitchers['away']['name'] if (pitchers.get('away') and isinstance(pitchers['away'], dict) and pitchers['away'].get('name')) else 'Unknown'

            # Fallback jika ET date tidak ada
            if not game_info['game_date_et']:
                try:
                    from src.collectors.polymarket import convert_utc_to_et
                    et_date, et_time = convert_utc_to_et(game['game_time'])
                    game_info['game_date_et'] = et_date
                    if game_info['game_time_et'] == 'N/A':
                        game_info['game_time_et'] = et_time
                except:
                    game_info['game_date_et'] = game['game_time'][:10]
            
            # Ganti game_id menggunakan generator baru
            new_game_id = generate_game_id(away_team, home_team, game_info['game_date_et'], game_info['game_time_et'])
            game_info['game_id'] = new_game_id
            
            # Fix 3: Tambahkan game_datetime_et ke game_info
            game_info['game_datetime_et'] = f"{game_info['game_date_et']} {game_info['game_time_et']}"

            logger.info("\n" + format_game_analysis(game_info, analysis))

            # SIMPAN PREDIKSI KE DATABASE (Non-blocking)
            game_info['raw_stats'] = game_full_data
            try:
                if save_prediction(game_info, analysis):
                    logger.info("💾 Prediksi disimpan")
            except Exception as db_err:
                logger.warning(f"⚠️ Gagal menyimpan prediksi: {db_err}")

            # g. Kirim Alert via Telegram (Jika memenuhi syarat dan belum pernah dikirim)
            send_high_confidence_alert(game_info, analysis)

            # --- SHADOW TESTING / EXPERIMENTS ---
            for version_name, overrides in EXPERIMENT_VERSIONS.items():
                if version_name == PRODUCTION_VERSION:
                    # Versi produksi cukup logging ulang hasil dari baris 210 tanpa hitung ulang
                    exp_runs = analysis["final_expected_runs"]
                    exp_rec = analysis["recommendation"]
                    exp_conf = analysis["confidence"]
                    exp_reasons = analysis["reasons"]
                else:
                    # Hitung ulang untuk versi eksperimen menggunakan params_override
                    try:
                        exp_analysis = calculate_expected_total_runs(game_full_data, params_override=overrides)
                        exp_runs = exp_analysis["final_expected_runs"]
                        exp_rec = make_recommendation(exp_runs, market_info['line'], params_override=overrides, volatility_score=exp_analysis['volatility_score'])
                        exp_conf = calculate_confidence(exp_runs, market_info['line'], params_override=overrides)
                        exp_reasons = exp_analysis["reasons"]
                    except Exception as calc_err:
                        logger.error(f"⚠️ Gagal menghitung ulang eksperimen {version_name}: {calc_err}")
                        continue
                
                # Simpan ke tabel experiment_predictions
                try:
                    # Gunakan game_info['game_id'] untuk menghubungkan ke game asli
                    log_experiment_prediction(
                        game_id=game_info.get('game_id'),
                        params_version=version_name,
                        expected_runs=exp_runs,
                        recommendation=exp_rec,
                        confidence=exp_conf,
                        key_factors=exp_reasons
                    )
                    logger.info(f"🧪 Shadow testing logged for version {version_name}")
                except Exception as db_err:
                    logger.warning(f"⚠️ Gagal menyimpan log eksperimen {version_name}: {db_err}")

            # Umpire Logging
            try:
                from src.collectors.umpire_collector import get_home_plate_umpire
                umpire = get_home_plate_umpire(mlb_api_game_id)
                if umpire:
                    conn = get_db_connection()
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn.execute("""
                        INSERT INTO umpire_log (game_id, umpire_name, predicted_runs, polymarket_line, logged_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (str(game_info.get('game_id')), umpire, analysis.get('final_expected_runs'), market_info.get('line'), now_str))
                    conn.commit()
                    conn.close()
                    logger.info(f"⚾ Umpire logged: {umpire}")
            except Exception as ump_err:
                logger.warning(f"⚠️ Gagal mencatat umpire: {ump_err}")

            # Simpan untuk Summary Akhir
            all_analyses.append({
                "game_info": game_info,
                "analysis": analysis
            })
        except Exception as e:
            import traceback
            logger.error(f"Kesalahan saat memproses game: {e}\n{traceback.format_exc()}")
            continue


    # 3. Print Daily Summary
    logger.info("[3/4] Menghasilkan Daily Summary...")
    logger.info("=" * 60)
    logger.info("\n" + format_daily_summary(all_analyses))
    logger.info("=" * 60)

    # Kirim Daily Summary via Telegram
    send_daily_summary(all_analyses, waiting_games)

    logger.info("[4/4] Analisis Selesai! Gunakan data ini dengan bijak.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLB Polymarket O/U Prediction Bot")
    parser.add_argument("--game", type=str, help="Analisis hanya satu game berdasarkan ID")
    parser.add_argument("--days", type=int, default=None, help="Jumlah hari ke depan untuk dianalisis (0=hari ini, 1=besok)")
    parser.add_argument("--verbose", action="store_true", help="Tampilkan detail skip dan log")
    parser.add_argument("--layer", type=str, choices=['early', 'final', 'revision'], help="Layer analisis")
    
    args = parser.parse_args()
    run_analysis(args)
