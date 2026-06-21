"""
Modul Sistem Alert (Phase 4 Automation).
Bertugas menyaring dan mengirimkan notifikasi hanya untuk prediksi HIGH confidence.
Mencegah spam dengan mencatat alert yang sudah dikirim di database.
"""

import sqlite3
from datetime import datetime
from src.database.db_setup import get_db_connection
from src.output.telegram_sender import send_game_analysis
from src.output.discord_sender import send_alert_embed
from src.utils.logger import logger

def setup_alert_table():
    """Memastikan tabel sent_alerts tersedia di database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_alerts (
            game_id TEXT PRIMARY KEY,
            sent_at TEXT,
            confidence TEXT,
            recommendation TEXT
        )
    """)
    conn.commit()
    conn.close()

def should_send_alert(game_id, recommendation, confidence):
    """
    Mengecek apakah alert layak dan belum pernah dikirim hari ini.
    Hanya mengirim jika confidence HIGH dan bukan SKIP.
    """
    if "HIGH" not in confidence or "SKIP" in recommendation:
        return False
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Cek apakah game_id ini sudah pernah dikirim
        cursor.execute("SELECT sent_at FROM sent_alerts WHERE game_id = ?", (str(game_id),))
        row = cursor.fetchone()
        
        # Jika belum ada di tabel, berarti belum pernah dikirim
        return row is None
    except Exception as e:
        logger.error(f"[Alert System] Error mengecek status alert: {e}")
        return False
    finally:
        conn.close()

def mark_alert_sent(game_id, recommendation, confidence):
    """
    Mencatat di database bahwa alert untuk game ini sudah dikirim.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT OR REPLACE INTO sent_alerts (game_id, sent_at, confidence, recommendation)
            VALUES (?, ?, ?, ?)
        """, (str(game_id), sent_at, confidence, recommendation))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"[Alert System] Error menandai alert: {e}")
        return False
    finally:
        conn.close()

def format_alert_message(analysis_result, channel="telegram"):
    """
    (Opsional) Fungsi ini bisa digunakan untuk merombak format spesifik per platform.
    Saat ini format markdown ditangani langsung oleh telegram_sender.py.
    Disediakan untuk kemudahan ekspansi Discord (embeds) ke depannya.
    """
    # Untuk Phase 4 saat ini kita pass-through ke struktur dictionary aslinya
    return analysis_result

def send_high_confidence_alert(game_info, analysis_result):
    """
    Fungsi utama untuk memproses dan mengirim alert jika memenuhi syarat.
    
    Args:
        game_info (dict): Data pertandingan.
        analysis_result (dict): Hasil analisis dan rekomendasi bot.
    """
    setup_alert_table()
    
    game_id = game_info.get("game_id")
    rec = analysis_result.get("recommendation", "")
    conf = analysis_result.get("confidence", "")
    
    if should_send_alert(game_id, rec, conf):
        logger.info(f"[Alert System] Mengirim HIGH confidence alert untuk game {game_id}...")
        
        # Kirim via Telegram (Telegram sender sudah disetup menerima dictionary ini)
        # Jika ada error jaringan di Telegram, telegram_sender tidak nge-crash.
        try:
            # Kirim via Telegram
            send_game_analysis(game_info, analysis_result)
            
            # Kirim via Discord
            send_alert_embed(game_info, analysis_result)
            
            # Tandai sudah terkirim agar tidak double-send pada refresh berikutnya
            mark_alert_sent(game_id, rec, conf)
            logger.info(f"[Alert System] Berhasil mengirim alert.")
        except Exception as e:
            logger.error(f"[Alert System] Gagal mengirim alert via channel: {e}")
    else:
        # Silently pass jika tidak masuk kriteria atau sudah pernah dikirim
        pass

if __name__ == "__main__":
    setup_alert_table()
    logger.info("Sistem alert siap digunakan.")