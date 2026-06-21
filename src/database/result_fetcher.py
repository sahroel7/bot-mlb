"""
Modul Fetcher Hasil Pertandingan.
Bertugas mengambil skor akhir dari MLB Stats API dan mengevaluasi akurasi prediksi.
"""

import requests
from datetime import datetime, timedelta
from src.database.db_setup import get_db_connection
from src.utils.logger import logger

MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"

def get_final_score(game_id):
    """
    Mengambil skor final pertandingan dari MLB API.
    
    Args:
        game_id (str/int): ID pertandingan.
        
    Returns:
        dict: Data skor jika sudah selesai/batal/ditunda, None jika belum.
    """
    url = f"{MLB_API_BASE_URL}/schedule?gamePk={game_id}"
    
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if "dates" not in data or not data["dates"]:
            return None
            
        game = data["dates"][0]["games"][0]
        status_code = game.get("status", {}).get("statusCode", "")
        status_abstract = game.get("status", {}).get("abstractGameState", "")
        
        # 'F' = Final, 'O' = Game Over, 'C' = Canceled, 'P' = Postponed
        if status_code in ["F", "O", "C", "P"] or status_abstract == "Final":
            home_runs = game.get("teams", {}).get("home", {}).get("score", 0)
            away_runs = game.get("teams", {}).get("away", {}).get("score", 0)
            innings = game.get("linescore", {}).get("currentInning", 9)
            
            return {
                "home_runs": home_runs,
                "away_runs": away_runs,
                "total_runs": home_runs + away_runs,
                "game_status": status_code,
                "innings_played": innings
            }
        else:
            # Game masih In Progress atau Scheduled
            return None
            
    except Exception as e:
        logger.error(f"[API Error] Gagal fetch skor untuk game {game_id}: {e}")
        return None

def save_result(game_id, final_score_data):
    """
    Menyimpan hasil aktual dan mengevaluasi kebenaran prediksi.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Ambil data prediksi terbaru untuk game ini
        pred_cursor = cursor.execute(
            "SELECT polymarket_line, bot_recommendation FROM predictions WHERE game_id = ? AND is_latest = 1", 
            (str(game_id),)
        )
        prediction = pred_cursor.fetchone()
        
        if not prediction:
            logger.error(f"[DB Error] Prediksi untuk game {game_id} tidak ditemukan.")
            return False
            
        line = prediction["polymarket_line"]
        rec = prediction["bot_recommendation"]
        
        # 2. Cek apakah game batal/ditunda
        status = final_score_data["game_status"]
        total_runs = final_score_data["total_runs"]
        
        # Validasi skor (Fix 6)
        if status not in ["F", "O", "C", "P"]:
            logger.info(f"[INFO] Game {game_id} belum Final. Status: {status}")
            return False
            
        if status not in ["C", "P"] and (total_runs == 0 or total_runs is None):
            logger.info(f"[INFO] Game {game_id} Final tapi skor 0-0 (belum valid). Menunggu update API.")
            return False
            
        if status in ["C", "P"]:
            # Void: Tidak dihitung benar maupun salah
            is_correct = None
            went_over = None
            logger.info(f"[INFO] Game {game_id} dibatalkan/ditunda. Status: Void.")
        else:
            total = total_runs
            
            # 3. Hitung actual Over/Under
            if total > line:
                went_over = 1
            elif total < line:
                went_over = 0
            else:
                went_over = None # Push (Seri dengan line, misal line 9.0 dan skor 9)
                
            # 4. Hitung Is Correct
            is_correct = None
            if "SKIP" in rec or went_over is None:
                is_correct = None
            elif "OVER" in rec and went_over == 1:
                is_correct = 1
            elif "OVER" in rec and went_over == 0:
                is_correct = 0
            elif "UNDER" in rec and went_over == 0:
                is_correct = 1
            elif "UNDER" in rec and went_over == 1:
                is_correct = 0
                
        # 5. Simpan ke database
        recorded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO results (
                game_id, actual_home_runs, actual_away_runs, actual_total_runs,
                went_over, is_correct, result_recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(game_id) DO UPDATE SET
                actual_home_runs = excluded.actual_home_runs,
                actual_away_runs = excluded.actual_away_runs,
                actual_total_runs = excluded.actual_total_runs,
                went_over = excluded.went_over,
                is_correct = excluded.is_correct,
                result_recorded_at = excluded.result_recorded_at
        """, (
            str(game_id), 
            final_score_data["home_runs"], 
            final_score_data["away_runs"], 
            final_score_data["total_runs"],
            went_over, 
            is_correct, 
            recorded_at
        ))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"[DB Error] Gagal menyimpan hasil {game_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_daily_performance(date_str):
    """
    Mengalkulasi ulang dan menyimpan ringkasan performa harian.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Agregasi data dari JOIN predictions dan results
        query = """
            SELECT 
                COUNT(p.id) as total_analyzed,
                SUM(CASE WHEN p.bot_recommendation != 'NO BET / SKIP ⚠️' AND p.bot_recommendation NOT LIKE '%SKIP%' THEN 1 ELSE 0 END) as total_bets,
                SUM(CASE WHEN r.is_correct = 1 THEN 1 ELSE 0 END) as total_correct,
                SUM(CASE WHEN r.is_correct = 0 THEN 1 ELSE 0 END) as total_incorrect,
                SUM(CASE WHEN r.is_correct = 1 AND p.bot_confidence LIKE '%HIGH%' THEN 1 ELSE 0 END) as high_correct,
                SUM(CASE WHEN r.is_correct = 0 AND p.bot_confidence LIKE '%HIGH%' THEN 1 ELSE 0 END) as high_incorrect
            FROM predictions p
            JOIN results r ON p.game_id = r.game_id
            WHERE p.game_date = ? AND p.is_latest = 1
        """
        cursor.execute(query, (date_str,))
        row = cursor.fetchone()
        
        total_analyzed = row['total_analyzed'] or 0
        total_bets = row['total_bets'] or 0
        correct = row['total_correct'] or 0
        incorrect = row['total_incorrect'] or 0
        high_c = row['high_correct'] or 0
        high_i = row['high_incorrect'] or 0
        
        # Hitung Win Rate (Hindari division by zero)
        resolved_bets = correct + incorrect
        win_rate = (correct / resolved_bets * 100.0) if resolved_bets > 0 else 0.0
        
        notes = "Updated automatically."
        
        # Simpan ke tabel daily_performance
        cursor.execute("""
            INSERT INTO daily_performance (
                date, total_games_analyzed, total_predictions_made, total_correct, total_incorrect,
                win_rate_daily, high_confidence_correct, high_confidence_incorrect, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_games_analyzed = excluded.total_games_analyzed,
                total_predictions_made = excluded.total_predictions_made,
                total_correct = excluded.total_correct,
                total_incorrect = excluded.total_incorrect,
                win_rate_daily = excluded.win_rate_daily,
                high_confidence_correct = excluded.high_confidence_correct,
                high_confidence_incorrect = excluded.high_confidence_incorrect,
                notes = excluded.notes
        """, (date_str, total_analyzed, total_bets, correct, incorrect, win_rate, high_c, high_i, notes))
        
        conn.commit()
        logger.info(f"[DB] Performa harian {date_str} diupdate: {win_rate:.1f}% WR ({correct}W - {incorrect}L)")
        return True
    except Exception as e:
        logger.error(f"[DB Error] Gagal update performa harian {date_str}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def process_yesterdays_results():
    """
    Fungsi utama yang mengambil skor untuk prediksi yang belum memiliki hasil (Final).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ambil semua game_id dari predictions yang belum ada di results, 
    # ATAU game-nya ada di results tapi belum Final (jika kita mau support re-check, meski saat ini hanya F yang masuk)
    # Kita ambil prediksi masa lalu (sebelum hari ini)
    today = datetime.now().strftime("%Y-%m-%d")
    
    query = """
        SELECT p.game_id, p.game_date 
        FROM predictions p 
        LEFT JOIN results r ON p.game_id = r.game_id
        WHERE r.id IS NULL AND p.game_date <= ? AND p.is_latest = 1
    """
    
    try:
        cursor.execute(query, (today,))
        pending_games = cursor.fetchall()
        
        if not pending_games:
            logger.info("[INFO] Tidak ada prediksi tertunda yang perlu diupdate hasilnya.")
            return 0
            
        logger.info(f"[INFO] Menemukan {len(pending_games)} game tertunda. Mengambil skor...")
        
        success_count = 0
        dates_to_update = set()
        
        for p in pending_games:
            g_id = p["game_id"]
            g_date = p["game_date"]
            
            score_data = get_final_score(g_id)
            if score_data:
                if save_result(g_id, score_data):
                    success_count += 1
                    dates_to_update.add(g_date)
            
        # Update daily performance untuk setiap tanggal yang ada perubahan
        for d in dates_to_update:
            update_daily_performance(d)
            
        return success_count
        
    except Exception as e:
        logger.error(f"[DB Error] Proses result fetcher gagal: {e}")
        return 0
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("--- Menjalankan Result Fetcher Manual ---")
    processed = process_yesterdays_results()
    logger.info(f"Selesai. {processed} game berhasil diupdate.")
