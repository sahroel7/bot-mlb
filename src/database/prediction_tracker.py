"""
Modul Tracker Prediksi.
Bertindak sebagai 'buku besar' (ledger) yang mencatat dan mengambil prediksi
real-time dari database SQLite.
"""

import sqlite3
import json
import os
from datetime import datetime
from src.database.db_setup import get_db_connection

def save_prediction(game_info, analysis_result, revision_reason=None):
    """
    Menyimpan atau memperbarui hasil analisis ke tabel predictions.
    Mendukung sistem versi (V1, V2, dst) jika ada revisi.
    
    Args:
        game_info (dict): Data game (id, team, venue, dll)
        analysis_result (dict): Hasil dari run_calculator
        revision_reason (str, optional): Alasan revisi (jika ini update)
        
    Returns:
        bool: True jika berhasil, False jika gagal.
    """
    if os.environ.get("BOT_DRY_RUN", "false").lower() == "true":
        print(f"[DRY RUN] [DB] save_prediction dipanggil untuk game {game_info.get('game_id')}. Data yang akan disimpan:")
        print(f"  Game: {game_info.get('away_team')} @ {game_info.get('home_team')} ({game_info.get('game_date_et') or game_info.get('game_date')})")
        print(f"  Polymarket Line: {game_info.get('polymarket_line')}")
        print(f"  Expected Runs: {analysis_result.get('final_expected_runs')}")
        print(f"  Recommendation: {analysis_result.get('recommendation')}")
        print(f"  Confidence: {analysis_result.get('confidence')}")
        return True

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Ekstraksi dan penyesuaian data
        game_id = str(game_info.get('game_id'))
        
        # Prioritaskan ET date agar sinkron dengan Polymarket
        game_date = game_info.get('game_date_et') or game_info.get('game_date') or game_info.get('game_time', '')[:10]
        
        home_team = game_info.get('home_team', '')
        away_team = game_info.get('away_team', '')
        venue = game_info.get('venue_name', '')
        polymarket_line = game_info.get('polymarket_line', 0.0)
        
        bot_expected_runs = analysis_result.get('final_expected_runs', 0.0)
        bot_recommendation = analysis_result.get('recommendation', 'SKIP')
        bot_confidence = analysis_result.get('confidence', 'LOW')
        
        # Ekstraksi dari full data
        pitcher_home = game_info.get('home_pitcher', 'Unknown')
        pitcher_away = game_info.get('away_pitcher', 'Unknown')
        weather_summary = game_info.get('weather_summary', 'Unknown')
        park_factor = game_info.get('park_factor', 100.0)
        
        key_factors_json = json.dumps(analysis_result.get('reasons', []))
        raw_stats_json = json.dumps(game_info.get('raw_stats', {}))
        
        # Tambahkan mod breakdown ke raw_stats_json jika ada di analysis_result
        if 'raw_stats' in game_info:
            raw_data_dict = game_info['raw_stats']
            raw_data_dict['mods'] = {
                'mod_pitcher': analysis_result.get('mod_pitcher', 0),
                'mod_offense': analysis_result.get('mod_offense', 0),
                'mod_env': analysis_result.get('mod_env', 0)
            }
            raw_stats_json = json.dumps(raw_data_dict)

        predicted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # New columns from analysis_result or game_info
        layer_type = analysis_result.get('layer_type')
        layer_sent_at = predicted_at if layer_type else None
        game_time_et_full = game_info.get('game_time_et', 'N/A')
        line_range = game_info.get('line_range', '-')

        # Cek apakah game_id sudah ada prediksi terbarunya (Sistem Versi)
        # PRIORITAS 1: Cek berdasarkan game_id
        cursor.execute("""
            SELECT id, version, bot_recommendation, daily_sequence, 
                   early_recommendation, early_expected_runs, early_confidence,
                   final_recommendation, final_expected_runs, final_confidence,
                   line_range, game_id, game_time_et
            FROM predictions WHERE game_id = ? ORDER BY version DESC LIMIT 1
        """, (game_id,))
        existing = cursor.fetchone()
        
        # PRIORITAS 2: Cek berdasarkan Matchup + Tanggal (Jika game_id beda tapi tim & hari sama)
        if not existing:
            cursor.execute("""
                SELECT id, version, bot_recommendation, daily_sequence, 
                       early_recommendation, early_expected_runs, early_confidence,
                       final_recommendation, final_expected_runs, final_confidence,
                       line_range, game_id, game_time_et
                FROM predictions 
                WHERE home_team = ? AND away_team = ? AND game_date = ? 
                AND (game_time_et = ? OR game_time_et IS NULL OR ? IS NULL)
                ORDER BY version DESC LIMIT 1
            """, (home_team, away_team, game_date, game_time_et_full, game_time_et_full))
            existing = cursor.fetchone()
            if existing:
                print(f"[DB] Matchup found with different game_id: {existing['game_id']} -> {game_id}. Syncing...")
        
        version = 1
        previous_recommendation = None
        daily_sequence = None
        
        early_rec = analysis_result.get('early_recommendation')
        early_exp = analysis_result.get('early_expected_runs')
        early_conf = analysis_result.get('early_confidence')
        
        final_rec = analysis_result.get('final_recommendation')
        final_exp = analysis_result.get('final_expected_runs')
        final_conf = analysis_result.get('final_confidence')
        
        if existing:
            version = existing['version'] + 1
            previous_recommendation = existing['bot_recommendation']
            daily_sequence = existing['daily_sequence']
            if not line_range or line_range == '-': line_range = existing['line_range']
                        
            # Carry over early/final if not provided in current run
            if not early_rec: early_rec = existing['early_recommendation']
            if not early_exp: early_exp = existing['early_expected_runs']
            if not early_conf: early_conf = existing['early_confidence']
            if not final_rec: final_rec = existing['final_recommendation']
            if not final_exp: final_exp = existing['final_expected_runs']
            if not final_conf: final_conf = existing['final_confidence']
            
            # Set SEMUA record lama untuk matchup ini menjadi bukan latest (mengantisipasi game_id ganda)
            cursor.execute("""
                UPDATE predictions 
                SET is_latest = 0 
                WHERE (game_id = ? OR (home_team = ? AND away_team = ? AND game_date = ?))
                AND is_latest = 1
            """, (game_id, home_team, away_team, game_date))
        else:
            # Jika ini prediksi V1 baru, hitung nomor urutan harian BERDASARKAN WIB
            target_date_for_seq = game_date
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM predictions 
                WHERE game_date = ?
                AND version = 1
            """, (target_date_for_seq,))
            count_res = cursor.fetchone()
            daily_sequence = (count_res['count'] or 0) + 1

        # Jika ini adalah layer early/final, update kolom spesifiknya
        if layer_type == 'early':
            early_rec = bot_recommendation
            early_exp = bot_expected_runs
            early_conf = bot_confidence
        elif layer_type == 'final':
            final_rec = bot_recommendation
            final_exp = bot_expected_runs
            final_conf = bot_confidence

        game_datetime_et = game_info.get('game_datetime_et')

        from src.utils.date_formatter import format_game_display
        try:
            formatted_date = format_game_display(game_date, game_time_et_full)
            game_time_wib = formatted_date['game_time_wib']
        except Exception as e:
            game_time_wib = None

        cursor.execute("""
            INSERT INTO predictions (
                game_id, version, is_latest, revision_reason, previous_recommendation, daily_sequence,
                game_date, game_time_et, game_time_wib, game_datetime_et, home_team, away_team, venue,
                polymarket_line, line_range, bot_expected_runs, bot_recommendation, bot_confidence,
                pitcher_home, pitcher_away, weather_summary, park_factor, key_factors, raw_stats, predicted_at,
                layer_type, layer_sent_at, early_recommendation, early_expected_runs, early_confidence,
                final_recommendation, final_expected_runs, final_confidence
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_id, version, revision_reason, previous_recommendation, daily_sequence,
            game_date, game_time_et_full, game_time_wib, game_datetime_et, home_team, away_team, venue,
            polymarket_line, line_range, bot_expected_runs, bot_recommendation, bot_confidence,
            pitcher_home, pitcher_away, weather_summary, park_factor, key_factors_json, raw_stats_json, predicted_at,
            layer_type, layer_sent_at, early_rec, early_exp, early_conf, final_rec, final_exp, final_conf
        ))
        
        conn.commit()
        print(f"[DB] Prediksi game {game_id} (v{version}) berhasil disimpan.")
        return True
    except Exception as e:
        print(f"[DB Error] Gagal menyimpan prediksi: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_latest_prediction(game_id):
    """
    Mencari prediksi spesifik terbaru berdasarkan game_id.
    
    Returns:
        dict: Data prediksi atau None jika tidak ditemukan.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM predictions WHERE game_id = ? AND is_latest = 1", (str(game_id),))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"[DB Error] Gagal mencari prediksi terbaru {game_id}: {e}")
        return None
    finally:
        conn.close()

def get_todays_predictions():
    """
    Mengambil semua prediksi terbaru yang dibuat hari ini.
    
    Returns:
        list: List of dict dari tabel predictions.
    """
    conn = get_db_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Mengambil prediksi berdasarkan tanggal game ATAU tanggal prediksi
        cursor = conn.execute("SELECT * FROM predictions WHERE (game_date = ? OR date(predicted_at) = ?) AND is_latest = 1", (today, today))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] Gagal mengambil prediksi hari ini: {e}")
        return []
    finally:
        conn.close()

def get_prediction_by_game_id(game_id):
    """
    Mencari prediksi spesifik berdasarkan game_id (deprecated, use get_latest_prediction).
    Tetap ada untuk kompatibilitas ke belakang, mengambil versi terbaru.
    """
    return get_latest_prediction(game_id)

def has_prediction_today(game_id):
    """
    Mengecek apakah prediksi terbaru untuk game ini sudah ada.
    """
    return get_latest_prediction(game_id) is not None

def get_prediction_history(days=30):
    """
    Mengambil semua prediksi terbaru dari N hari terakhir beserta hasilnya (jika ada).
    Melakukan JOIN tabel predictions dengan tabel results.
    
    Returns:
        list: List of dict berisi prediksi dan hasil aktualnya.
    """
    conn = get_db_connection()
    from datetime import timedelta
    target_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    query = """
        SELECT 
            p.*, 
            r.actual_home_runs, r.actual_away_runs, r.actual_total_runs, 
            r.went_over, r.is_correct, r.result_recorded_at
        FROM predictions p
        LEFT JOIN results r ON p.game_id = r.game_id
        WHERE p.game_date >= ? AND p.is_latest = 1
        ORDER BY p.game_date DESC, p.game_time_et DESC
    """
    
    try:
        cursor = conn.execute(query, (target_date,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] Gagal mengambil histori prediksi: {e}")
        return []
    finally:
        conn.close()

def log_experiment_prediction(game_id, params_version, expected_runs, recommendation, confidence, key_factors, volatility_score=0):
    """
    Menyimpan prediksi eksperimen ke tabel experiment_predictions.
    
    Args:
        game_id (str): ID game MLB.
        params_version (str): Versi/nama eksperimen parameter (misal: 'v2.1_higher_gap').
        expected_runs (float): Prediksi expected total runs.
        recommendation (str): Hasil rekomendasi (OVER/UNDER/SKIP).
        confidence (str): Tingkat kepercayaan (HIGH/MEDIUM/LOW).
        key_factors (list/str): Faktor kunci/reasons.
        volatility_score (int): Skor volatilitas game.
        
    Returns:
        bool: True jika berhasil, False jika gagal.
    """
    logged_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Handle list key_factors
    if isinstance(key_factors, list):
        key_factors_json = json.dumps(key_factors)
    else:
        key_factors_json = str(key_factors)

    if os.environ.get("BOT_DRY_RUN", "false").lower() == "true":
        print(f"[DRY RUN] [DB] log_experiment_prediction dipanggil untuk game {game_id} (versi: {params_version}). Data:")
        print(f"  Expected Runs: {expected_runs}")
        print(f"  Recommendation: {recommendation}")
        print(f"  Confidence: {confidence}")
        return True

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO experiment_predictions (
                game_id, params_version, expected_runs, recommendation, confidence, key_factors, logged_at, volatility_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(game_id) if game_id is not None else None, params_version, expected_runs, recommendation, confidence, key_factors_json, logged_at, volatility_score
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB Error] Gagal menyimpan prediksi eksperimen: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
