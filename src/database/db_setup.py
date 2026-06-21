"""
Modul Manajemen Database.
Bertanggung jawab untuk inisialisasi dan pengelolaan struktur database SQLite.
Digunakan untuk melacak prediksi real-time dan evaluasi hasil pertandingan.
"""

import sqlite3
import os

DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "mlb_bot.db")

def get_db_connection():
    """
    Menghasilkan objek koneksi SQLite yang siap digunakan.
    
    Returns:
        sqlite3.Connection: Koneksi database.
    """
    # Pastikan folder 'data' ada
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        
    conn = sqlite3.connect(DB_PATH)
    # Mengembalikan data dalam bentuk dictionary-like (memudahkan akses nama kolom)
    conn.row_factory = sqlite3.Row 
    return conn

def initialize_database():
    """
    Membuat semua tabel yang dibutuhkan bot jika belum ada.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- TABEL 1: PREDICTIONS ---
    # Mencatat prediksi harian yang dibuat bot SEBELUM game dimulai.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            version INTEGER DEFAULT 1,
            is_latest INTEGER DEFAULT 1,
            revision_reason TEXT DEFAULT NULL,
            previous_recommendation TEXT DEFAULT NULL,
            game_date TEXT,
            game_time_et TEXT,
            game_time_wib TEXT DEFAULT NULL,
            home_team TEXT,
            away_team TEXT,
            venue TEXT,
            polymarket_line REAL,
            bot_expected_runs REAL,
            bot_recommendation TEXT,
            bot_confidence TEXT,
            pitcher_home TEXT,
            pitcher_away TEXT,
            weather_summary TEXT,
            park_factor REAL,
            key_factors TEXT,
            raw_stats TEXT,
            predicted_at TEXT,
            user_checked INTEGER DEFAULT 0,
            checked_at TEXT DEFAULT NULL,
            daily_sequence INTEGER DEFAULT NULL,
            layer_type TEXT DEFAULT NULL,
            layer_sent_at TEXT DEFAULT NULL,
            early_recommendation TEXT DEFAULT NULL,
            early_expected_runs REAL DEFAULT NULL,
            early_confidence TEXT DEFAULT NULL,
            final_recommendation TEXT DEFAULT NULL,
            final_expected_runs REAL DEFAULT NULL,
            final_confidence TEXT DEFAULT NULL,
            line_range TEXT DEFAULT NULL,
            game_datetime_et TEXT DEFAULT NULL,
            UNIQUE(game_id, version)
        )
    """)
    
    # Coba tambahkan kolom raw_stats jika tabel sudah ada dari versi sebelumnya
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN raw_stats TEXT")
    except sqlite3.OperationalError:
        pass # Kolom sudah ada

    # Tambahkan kolom checklist personal
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN user_checked INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN checked_at TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    # Tambahkan kolom game_time_wib jika belum ada
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN game_time_wib TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    # --- TABEL 2: RESULTS ---
    # Mencatat hasil aktual SETELAH game selesai dan mengkalkulasi is_correct.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            actual_home_runs INTEGER,
            actual_away_runs INTEGER,
            actual_total_runs INTEGER,
            went_over INTEGER,
            is_correct INTEGER,
            result_recorded_at TEXT,
            FOREIGN KEY(game_id) REFERENCES predictions(game_id)
        )
    """)

    # --- TABEL 3: DAILY PERFORMANCE ---
    # Ringkasan performa harian bot (Aggregasi).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_performance (
            date TEXT PRIMARY KEY,
            total_games_analyzed INTEGER,
            total_predictions_made INTEGER,
            total_correct INTEGER,
            total_incorrect INTEGER,
            win_rate_daily REAL,
            high_confidence_correct INTEGER,
            high_confidence_incorrect INTEGER,
            notes TEXT
        )
    """)

    conn.commit()
    conn.close()

def migrate_add_revision_columns():
    """
    Migrasi tabel predictions untuk menambahkan fitur revisi:
    - version, is_latest, revision_reason, previous_recommendation
    - mengubah constraint dari UNIQUE(game_id) ke UNIQUE(game_id, version)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Cek apakah kolom version sudah ada
    cursor.execute("PRAGMA table_info(predictions)")
    columns = [col['name'] for col in cursor.fetchall()]
    
    if 'version' not in columns:
        print("[DB Migration] Melakukan migrasi tabel predictions untuk fitur revisi...")
        
        # 1. Buat tabel temp dengan struktur baru
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                version INTEGER DEFAULT 1,
                is_latest INTEGER DEFAULT 1,
                revision_reason TEXT DEFAULT NULL,
                previous_recommendation TEXT DEFAULT NULL,
                game_date TEXT,
                game_time_et TEXT,
                home_team TEXT,
                away_team TEXT,
                venue TEXT,
                polymarket_line REAL,
                bot_expected_runs REAL,
                bot_recommendation TEXT,
                bot_confidence TEXT,
                pitcher_home TEXT,
                pitcher_away TEXT,
                weather_summary TEXT,
                park_factor REAL,
                key_factors TEXT,
                raw_stats TEXT,
                predicted_at TEXT,
                UNIQUE(game_id, version)
            )
        """)
        
        # 2. Copy data dari tabel lama ke tabel baru
        try:
            cursor.execute("""
                INSERT INTO predictions_new (
                    game_id, version, is_latest, game_date, game_time_et, home_team, away_team, venue,
                    polymarket_line, bot_expected_runs, bot_recommendation, bot_confidence,
                    pitcher_home, pitcher_away, weather_summary, park_factor, key_factors, raw_stats, predicted_at
                )
                SELECT game_id, 1, 1, game_date, game_time_et, home_team, away_team, venue,
                    polymarket_line, bot_expected_runs, bot_recommendation, bot_confidence,
                    pitcher_home, pitcher_away, weather_summary, park_factor, key_factors, raw_stats, predicted_at
                FROM predictions
            """)
        except Exception as e:
            print(f"[DB Migration Error] Gagal memindahkan data: {e}")
            conn.rollback()
            return
            
        # 3. Drop tabel lama
        cursor.execute("DROP TABLE predictions")
        
        # 4. Rename tabel baru menjadi tabel lama
        cursor.execute("ALTER TABLE predictions_new RENAME TO predictions")
        
        conn.commit()
        print("[DB Migration] Migrasi berhasil!")
    else:
        print("[DB Migration] Tabel predictions sudah memiliki kolom revisi. Skip migrasi.")
        
    conn.close()

# Panggil fungsi inisialisasi secara otomatis saat modul ini di-import
initialize_database()
migrate_add_revision_columns()

if __name__ == "__main__":
    print(f"✅ Setup database berhasil dijalankan.")
    print(f"📂 Lokasi Database: {os.path.abspath(DB_PATH)}")
    
    # Verifikasi tabel
    conn = get_db_connection()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    conn.close()
    
    print("\nTabel yang tersedia:")
    for t in tables:
        print(f"- {t['name']}")
