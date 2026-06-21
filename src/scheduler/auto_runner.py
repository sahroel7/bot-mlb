"""
Modul Scheduler / Auto Runner (Phase 4 Automation) dengan Sistem Revisi.
Bertugas menjalankan bot secara otomatis 24/7 dan membuat jadwal dinamis 
untuk pengecekan revisi.
"""

import os
import sys
import time
import signal
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# Pastikan sys.path mencakup root direktori
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.logger import logger
from src.database.db_setup import get_db_connection
from src.database.prediction_tracker import get_latest_prediction
from src.database.result_fetcher import process_yesterdays_results
from src.output.telegram_sender import send_async_message
import asyncio

# Collectors for checking changes
from src.collectors.mlb_schedule import get_todays_games
from src.collectors.pitcher_stats import get_starting_pitchers
from src.collectors.polymarket import get_ou_line

class GracefulKiller:
    """Menangani signal sistem untuk mematikan bot dengan aman."""
    kill_now = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True
        logger.info("[SYSTEM] Menerima sinyal terminasi. Menutup bot dengan aman...")

class DummyArgs:
    """Kelas tiruan untuk args yang dibutuhkan oleh run_analysis"""
    def __init__(self):
        self.game = None
        self.verbose = False
        self.days = None

def run_early_alert():
    """Jadwal 09:00 WIB: EARLY ALERT untuk game besok (V1)."""
    logger.info("=== MENJALANKAN EARLY ALERT (09:00 WIB) UNTUK BESOK ===")
    from main import run_analysis
    try:
        args = DummyArgs()
        args.days = 1 # Game besok
        args.layer = 'early'
        run_analysis(args)
    except Exception as e:
        logger.error(f"Early Alert gagal: {e}")

def run_final_alert():
    """Jadwal 15:00 WIB: FINAL ALERT untuk game hari ini."""
    logger.info("=== MENJALANKAN FINAL ALERT (15:00 WIB) UNTUK HARI INI ===")
    from main import run_analysis
    try:
        args = DummyArgs()
        args.days = 0 # Game hari ini
        args.layer = 'final'
        run_analysis(args)
        
        # Setelah Final Alert, jadwalkan revisi dinamis
        schedule_revision_analysis()
    except Exception as e:
        logger.error(f"Final Alert gagal: {e}")

def schedule_revision_analysis():
    """Membaca prediksi yang is_latest=1, hitung T-3 jam, dan jadwalkan pengecekan."""
    logger.info("=== SCHEDULING DYNAMIC REVISIONS ===")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT game_id, game_date, game_time_et, home_team, away_team 
            FROM predictions 
            WHERE (game_date = ? OR game_date = ?) AND is_latest = 1
        """, (today, tomorrow))
        games = cursor.fetchall()
        
        for g in games:
            game_id = g['game_id']
            
            # Parsing waktu ET dan konversi kasar ke WIB (+11 jam dari ET)
            # Lalu kurangi 3 jam untuk revisi (Net: +8 jam dari ET)
            try:
                et_time = datetime.strptime(f"{g['game_date']} {g['game_time_et']}", "%Y-%m-%d %H:%M:%S")
                # Konversi ET ke WIB (Estimasi +11 jam)
                wib_time = et_time + timedelta(hours=11)
                # T-3 jam sebelum game
                revision_time = wib_time - timedelta(hours=3)
                
                # Jika waktu revisi sudah lewat, abaikan (atau jalankan segera jika mau)
                if revision_time < datetime.now():
                    logger.info(f"Revision time for {game_id} already passed. Skipping.")
                    continue

                logger.info(f"Menjadwalkan cek revisi untuk game {game_id} ({g['away_team']} @ {g['home_team']}) pada {revision_time}")
                
                scheduler.add_job(
                    check_for_changes,
                    'date',
                    run_date=revision_time,
                    args=[game_id],
                    id=f'rev_{game_id}',
                    replace_existing=True
                )
            except Exception as e:
                logger.error(f"Gagal parsing waktu untuk game {game_id}: {e}")
                # Fallback: 1 jam dari sekarang jika gagal parsing
                revision_time = datetime.now() + timedelta(hours=1)
            
    except Exception as e:
        logger.error(f"Gagal menjadwalkan revisi: {e}")
    finally:
        conn.close()

def classify_revision_level(v1_data, v2_data):
    """Menentukan tingkat perubahan antara V1 dan V2."""
    v1_rec = v1_data.get('bot_recommendation', '')
    v2_rec = v2_data.get('bot_recommendation', '')
    
    v1_conf = v1_data.get('bot_confidence', '')
    v2_conf = v2_data.get('bot_confidence', '')
    
    v1_exp = v1_data.get('bot_expected_runs', 0.0)
    v2_exp = v2_data.get('bot_expected_runs', 0.0)
    
    # 1. Arah berubah (OVER <-> UNDER)
    v1_dir = "OVER" if "OVER" in v1_rec else "UNDER" if "UNDER" in v1_rec else "SKIP"
    v2_dir = "OVER" if "OVER" in v2_rec else "UNDER" if "UNDER" in v2_rec else "SKIP"
    if v1_dir != v2_dir and v1_dir != "SKIP" and v2_dir != "SKIP":
        return "CRITICAL"
        
    # 2. Confidence berubah level (LOW->HIGH, dll)
    levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
    v1_lvl = levels.get(next((lvl for lvl in levels if lvl in v1_conf), "LOW"), 1)
    v2_lvl = levels.get(next((lvl for lvl in levels if lvl in v2_conf), "LOW"), 1)
    
    if abs(v2_lvl - v1_lvl) >= 2:
        return "IMPORTANT"
        
    # 3. Expected runs berubah > 1.5
    if abs(v2_exp - v1_exp) > 1.5:
        return "INFORMATIVE"
        
    return "SKIP"

def check_for_changes(game_id):
    """Job 2: Mengecek apakah ada perubahan kondisi (pitcher/cuaca/line)."""
    logger.info(f"=== CHECKING FOR CHANGES: GAME {game_id} ===")
    v1_data = get_latest_prediction(game_id)
    if not v1_data:
        logger.info(f"Game {game_id} tidak memiliki prediksi V1.")
        return
        
    home_team = v1_data['home_team']
    away_team = v1_data['away_team']
    
    # A. Cek Line
    market_info = get_ou_line(home_team, away_team)
    new_line = market_info['line'] if market_info else v1_data['polymarket_line']
    line_diff = abs(new_line - v1_data['polymarket_line'])
    
    # B. Cek Pitcher
    pitchers = get_starting_pitchers(game_id)
    new_home_pitcher = "Unknown"
    new_away_pitcher = "Unknown"
    if pitchers['home'] and 'name' in pitchers['home']:
        new_home_pitcher = pitchers['home']['name']
    if pitchers['away'] and 'name' in pitchers['away']:
        new_away_pitcher = pitchers['away']['name']
        
    pitcher_changed = (new_home_pitcher != v1_data['pitcher_home'] and new_home_pitcher != "Unknown") or \
                      (new_away_pitcher != v1_data['pitcher_away'] and new_away_pitcher != "Unknown")
                      
    revision_reason = []
    if line_diff > 0.5:
        revision_reason.append(f"Line Bullpen bergerak ({v1_data['polymarket_line']} -> {new_line})")
    if pitcher_changed:
        revision_reason.append("Starting pitcher diganti")
        
    if not revision_reason:
        logger.info(f"No changes detected for {game_id}, skipping revision.")
        return
        
    reason_str = " & ".join(revision_reason)
    logger.info(f"Perubahan terdeteksi: {reason_str}. Menjalankan re-analisis.")
    
    try:
        from main import run_analysis
        args = DummyArgs()
        args.game = str(game_id)
        
        # Override modul get_latest_prediction sementara bisa dilakukan dengan state passing,
        # tapi karena main memanggil save_prediction, kita harus passing revision_reason ke run_calculator
        # Sebagai workaround MVP, setelah run_analysis selesai, kita update DB record terbaru dengan revision_reason
        run_analysis(args) 
        
        v2_data = get_latest_prediction(game_id)
        
        if v2_data and v2_data['version'] > v1_data['version']:
            # Update reason di DB
            conn = get_db_connection()
            conn.execute("UPDATE predictions SET revision_reason = ? WHERE id = ?", (reason_str, v2_data['id']))
            conn.commit()
            conn.close()
            
            level = classify_revision_level(v1_data, v2_data)
            
            if level == "CRITICAL":
                msg = f"⚠️ *REVISI KRITIS — Arah Berubah*\n"
                msg += f"Game: {away_team} @ {home_team}\n"
                msg += f"{v1_data['bot_recommendation']} -> {v2_data['bot_recommendation']}\n"
                msg += f"Alasan: {reason_str}"
                asyncio.run(send_async_message(msg))
            elif level == "IMPORTANT":
                msg = f"📊 *REVISI PENTING — Keyakinan Berubah*\n"
                msg += f"Game: {away_team} @ {home_team}\n"
                msg += f"{v1_data['bot_confidence']} -> {v2_data['bot_confidence']}\n"
                msg += f"Expected: {v1_data['bot_expected_runs']} -> {v2_data['bot_expected_runs']}\n"
                msg += f"Alasan: {reason_str}"
                asyncio.run(send_async_message(msg))
            elif level == "INFORMATIVE":
                msg = f"📈 *UPDATE PREDIKSI*\n"
                msg += f"Game: {away_team} @ {home_team}\n"
                msg += f"Expected runs: {v1_data['bot_expected_runs']} -> {v2_data['bot_expected_runs']}\n"
                msg += f"Rekomendasi tetap: {v2_data['bot_recommendation']}"
                asyncio.run(send_async_message(msg))
                
    except Exception as e:
        logger.error(f"Gagal re-analisis untuk {game_id}: {e}")

def run_results_check():
    """Job 3: Jam 08:00 WIB, ambil hasil game kemarin dan kirim report."""
    logger.info("=== MENJALANKAN SCHEDULED RESULTS CHECK ===")
    processed = process_yesterdays_results()
    
    # Kirim Laporan ke Telegram
    from src.output.telegram_sender import send_daily_results
    from datetime import date, timedelta
    
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
      SELECT p.away_team, p.home_team, p.game_date,
             p.polymarket_line, p.bot_recommendation,
             p.bot_confidence, r.actual_total_runs,
             r.is_correct
      FROM predictions p
      LEFT JOIN results r ON p.game_id = r.game_id
      WHERE p.game_date = ?
      AND p.is_latest = 1
      AND p.bot_recommendation NOT LIKE '%SKIP%'
    ''', (yesterday,))
    rows = cursor.fetchall()
    conn.close()
    
    if rows:
        logger.info(f"Mengirim laporan harian untuk {yesterday}...")
        send_daily_results(rows, yesterday)
    
    if processed > 0:
        logger.info(f"{processed} hasil pertandingan baru berhasil diupdate.")

def job_line_movement_check():
    """Job 4: Cek pergerakan odds setiap 30 menit (Placeholder)."""
    logger.info("=== CHECKING POLYMARKET LINE MOVEMENT ===")
    pass

# Global scheduler
scheduler = BackgroundScheduler()

def job_check_waiting_markets():
    """Cek game yang ada di waiting_markets dan coba analisis jika market sudah buka."""
    logger.info("=== CHECKING WAITING MARKETS ===")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM waiting_markets WHERE status = 'pending'")
        rows = cursor.fetchall()
        
        if not rows:
            logger.info("Tidak ada game di antrean waiting_markets.")
            return

        from main import run_analysis
        
        for row in rows:
            game_id = row['game_id']
            away = row['away_team']
            home = row['home_team']
            
            logger.info(f"Mengecek market untuk {away} @ {home} (ID: {game_id})")
            
            # Cek apakah market sudah ada
            market_info = get_ou_line(home, away)
            if market_info:
                logger.info(f"Market ditemukan untuk {game_id}! Menjalankan analisis...")
                args = DummyArgs()
                args.game = str(game_id)
                # Tandai sebagai final alert jika ini market baru yang terbuka
                args.layer = 'final'
                
                try:
                    run_analysis(args)
                    # Jika sukses, hapus dari waiting_markets
                    cursor.execute("DELETE FROM waiting_markets WHERE game_id = ?", (game_id,))
                    conn.commit()
                except Exception as e:
                    logger.error(f"Gagal analisis market baru {game_id}: {e}")
            else:
                # Update last checked
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("UPDATE waiting_markets SET last_checked_at = ? WHERE game_id = ?", (now_str, game_id))
                conn.commit()
                
    except Exception as e:
        logger.error(f"Error pada job_check_waiting_markets: {e}")
    finally:
        conn.close()

def run_auto_scheduler():
    """Fungsi utama scheduler."""
    logger.info("Menginisialisasi Dynamic Auto Runner (Phase 4.1)...")
    
    # 1. Jadwal Results Check (Jam 08:00) - Tetap aktif untuk sinkronisasi hasil & akurasi
    scheduler.add_job(
        run_results_check,
        CronTrigger(hour=8, minute=0),
        id='daily_results'
    )

    # Note: Automated alert schedulers (Early Alert, Final Alert, Line Movement, and Waiting Markets) 
    # have been disabled to allow exclusive on-demand predictions via "/prediksi" command.
    
    scheduler.start()
    logger.info("Scheduler aktif (Background).")

    # 5. Jalankan Bot Listener (Interaktif) di Main Thread
    # Ini akan mem-block eksekusi di sini
    from src.output.telegram_bot import run_bot_listener
    try:
        run_bot_listener()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        scheduler.shutdown()
        logger.info("Bot berhasil dimatikan.")

if __name__ == "__main__":
    run_auto_scheduler()
