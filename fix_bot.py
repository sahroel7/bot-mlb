import urllib.request
# Just creating a placeholder python script to write to the file
content = '''"""
Modul Listener Bot Telegram (Phase 4 Enhancement).
Menangani command interaktif dan callback button.
TIDAK MENYENTUH LOGIKA PREDIKSI APAPUN.
"""

import os
import json
import asyncio
import pytz
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

from src.utils.logger import logger
from src.database.db_setup import get_db_connection
from src.utils.bullpen_url_generator import generate_bullpen_url

# Import untuk /prediksi
from src.collectors.mlb_schedule import get_upcoming_games
from src.collectors.polymarket import get_ou_line
from src.collectors.pitcher_stats import (
    get_starting_pitchers, get_pitcher_season_stats, 
    get_pitcher_last_3_starts, get_bullpen_era
)
from src.collectors.team_offense import (
    get_team_season_offense, get_team_last_10_games, calculate_streak
)
from src.collectors.weather import get_game_weather
from src.data.park_factors import get_park_factor
from src.processors.run_calculator import (
    calculate_expected_total_runs, make_recommendation, calculate_confidence
)
from src.database.prediction_tracker import save_prediction, get_latest_prediction

# Load env
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

TEAM_SHORT_NAME = {
    "Arizona Diamondbacks": "ARI D-backs",
    "Atlanta Braves": "ATL Braves",
    "Baltimore Orioles": "BAL Orioles",
    "Boston Red Sox": "BOS Red Sox",
    "Chicago Cubs": "CHI Cubs",
    "Chicago White Sox": "CHI Sox",
    "Cincinnati Reds": "CIN Reds",
    "Cleveland Guardians": "CLE Guard",
    "Colorado Rockies": "COL Rockies",
    "Detroit Tigers": "DET Tigers",
    "Houston Astros": "HOU Astros",
    "Kansas City Royals": "KC Royals",
    "Los Angeles Angels": "LA Angels",
    "Los Angeles Dodgers": "LA Dodgers",
    "Miami Marlins": "MIA Marlins",
    "Milwaukee Brewers": "MIL Brewers",
    "Minnesota Twins": "MIN Twins",
    "New York Mets": "NY Mets",
    "New York Yankees": "NY Yankees",
    "Oakland Athletics": "OAK Athletics",
    "Athletics": "Athletics",
    "Philadelphia Phillies": "PHI Phillies",
    "Pittsburgh Pirates": "PIT Pirates",
    "San Diego Padres": "SD Padres",
    "San Francisco Giants": "SF Giants",
    "Seattle Mariners": "SEA Mariners",
    "St. Louis Cardinals": "STL Cards",
    "Tampa Bay Rays": "TAM Rays",
    "Texas Rangers": "TEX Rangers",
    "Toronto Blue Jays": "TOR B. Jays",
    "Washington Nationals": "WAS Nats"
}

# Mapping Nama Hari Indonesia
HARI_MAP = {
    'Monday': 'Senin',
    'Tuesday': 'Selasa',
    'Wednesday': 'Rabu',
    'Thursday': 'Kamis',
    'Friday': 'Jumat',
    'Saturday': 'Sabtu',
    'Sunday': 'Minggu'
}

# ==========================================
# 1. FUNGSI HELPER
# ==========================================

def get_predictions_by_date(target_date, checked_status=None):
    """
    Query database predictions dengan filter tanggal (ET) dan status checklist.
    target_date: Format 'YYYY-MM-DD' mengacu pada game_date.
    Selalu mengambil versi terbaru (is_latest=1).
    Deduplikasi otomatis berdasarkan matchup jika terjadi keanehan game_id ganda.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ambil is_latest=1
    query = "SELECT * FROM predictions WHERE game_date = ? AND is_latest = 1 ORDER BY daily_sequence IS NULL, daily_sequence ASC, version DESC"
    
    cursor.execute(query, (target_date,))
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    seen_matchups = set() # Untuk deduplikasi (Away @ Home + Time)
    
    for row in rows:
        d = dict(row)
        
        # Deduplikasi: Jika matchup yang sama di waktu yang sama muncul lagi (beda game_id mungkin)
        # Gunakan kombinasi Away, Home, dan Waktu ET sebagai key
        matchup_key = f"{d['away_team']}_{d['home_team']}_{d['game_time_et']}"
        if matchup_key in seen_matchups:
            continue
        seen_matchups.add(matchup_key)

        if d['daily_sequence'] is None:
            # Fallback sequence jika null
            d['daily_sequence'] = len(result) + 1
            
        if checked_status is None or d['user_checked'] == checked_status:
            result.append(d)
            
    return result

def format_telegram_reasons(reasons_str):
    """Memformat list reasons menjadi string dengan emoji."""
    if not reasons_str:
        return ""
    try:
        reasons = json.loads(reasons_str)
    except:
        reasons = []
        
    formatted = []
    for reason in reasons:
        emoji = "•"
        if any(x in reason for x in ["Pitcher", "ERA", "K/9"]):
            emoji = "⚾"
        elif any(x in reason for x in ["Suhu", "Angin", "Cuaca", "Lembap"]):
            emoji = "🌡️"
        elif any(x in reason for x in ["Park", "Field"]):
            emoji = "🏟️"
        elif any(x in reason for x in ["Offense", "Streak", "RISP", "Momentum"]):
            emoji = "💪"
        formatted.append(f"  {emoji} {reason}")
    return "\\n".join(formatted)

def format_prediction_detail(pred, show_revision_label=True):
    """Format LENGKAP untuk satu game."""
    seq = pred.get('daily_sequence')
    seq_str = f"#{seq}" if seq is not None else "#?"
    
    # Handle revisi
    rev_str = "🔄 REVISI — " if show_revision_label and pred.get('version', 1) > 1 else ""
    
    away = pred.get('away_team', 'Unknown')
    home = pred.get('home_team', 'Unknown')
    
    raw_date = pred.get('game_date', '')
    try:
        dt = datetime.strptime(raw_date, "%Y-%m-%d")
        day_en = dt.strftime("%A")
        day_id = HARI_MAP.get(day_en, day_en)
        date_str = f"{day_id}, {dt.strftime('%d %b %Y')} ET"
    except:
        date_str = raw_date
        
    et_time = pred.get('game_time_et', 'N/A')
    line_range = pred.get('line_range', pred.get('polymarket_line', '-'))
    
    msg = f"{seq_str} {rev_str}🏟️ {away} @ {home}\\n"
    msg += f"📅 {date_str} | ⏰ {et_time}\\n"
    msg += "────────────────────────────\\n"
    msg += f"📊 Line Analisis : {pred.get('polymarket_line', '-')}\\n"
    msg += f"📏 Rentang Line  : {line_range}\\n"
    msg += f"🎯 Bot Expected     : {pred.get('bot_expected_runs', 0)}\\n"
    msg += f"📈 Recommendation   : {pred.get('bot_recommendation', 'SKIP')}\\n"
    msg += f"🔥 Confidence       : {pred.get('bot_confidence', 'LOW')}\\n"
    
    if pred.get('user_checked'):
        checked_dt = ""
        if pred.get('checked_at'):
            try:
                dt = datetime.fromisoformat(pred['checked_at'])
                checked_dt = f" ({dt.strftime('%H:%M')})"
            except:
                pass
        msg += f"🛒 Status           : ✅ Sudah Dibeli{checked_dt}\\n"
        
    msg += "📡 Sumber Odds      : Bullpen CLI\\n\\n"
    msg += "📋 KEY FACTORS:\\n"
    msg += format_telegram_reasons(pred.get('key_factors', '[]'))
    
    return msg

def format_prediction_ringkas(pred, index=None):
    """Format SATU BARIS untuk ringkasan."""
    seq = pred.get('daily_sequence')
    seq_str = f"#{seq}" if seq is not None else "#?"
    
    away_abbr = TEAM_SHORT_NAME.get(pred.get('away_team', '???'), pred.get('away_team', '???')[:12])
    home_abbr = TEAM_SHORT_NAME.get(pred.get('home_team', '???'), pred.get('home_team', '???')[:12])
    
    rec = pred.get('bot_recommendation', 'SKIP')
    conf = pred.get('bot_confidence', 'LOW')
    
    if "SKIP" in rec or "LOW" in conf:
        rec_label = "SKIP"
        conf_emoji = "⚠️"
    else:
        rec_label = rec.replace('OVER', 'OVR').replace('UNDER', 'UND')
        conf_emoji = "🔥" if "HIGH" in conf else "⚡"
        
    line = pred.get('polymarket_line', '-')
    et_time = pred.get('game_time_et', 'N/A')
    
    return f"{seq_str} {away_abbr} @ {home_abbr} | {rec_label} {conf_emoji} | {line} | {et_time}"

def build_game_keyboard(game_id, user_checked, away, home, game_date):
    """Membuat InlineKeyboardMarkup untuk game."""
    game_url = generate_bullpen_url(away, home, game_date)
    buttons = [
        [InlineKeyboardButton("💰 Buka Bullpen.fi", url=game_url)]
    ]
    
    if user_checked == 1:
        buttons.append([
            InlineKeyboardButton("✅ Sudah Dibeli | 🔄 Batalkan", callback_data=f"uncheck_{game_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton("☑️ Tandai Sudah Beli", callback_data=f"check_{game_id}")
        ])
        
    return InlineKeyboardMarkup(buttons)

# ==========================================
# 2. COMMAND HANDLERS
# ==========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /start."""
    await update.message.reply_text(
        "⚾ *MLB AI Bot Interactive Mode*\\n"
        "Gunakan /help untuk melihat daftar command.",
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /help."""
    help_text = (
        "📋 *Daftar Command MLB AI Bot:*\\n\\n"
        "/besok - Prediksi untuk pertandingan besok (ET)\\n"
        "/hari_ini - Prediksi untuk pertandingan hari ini (ET)\\n"
        "/sudah - Daftar game yang sudah dibeli\\n"
        "/belum - Daftar game besok yang belum dibeli\\n"
        "/akurasi - Statistik win rate bot\\n"
        "/top - 5 Prediksi HIGH confidence terkuat\\n"
        "/revisi - Daftar prediksi yang direvisi (V2)\\n"
        "/prediksi - Jalankan analisis ulang manual sekarang\\n"
        "/histori [hari] - Ringkasan histori (default 7 hari)\\n"
        "/game [tim] - Cari prediksi tim tertentu\\n"
        "/help - Tampilkan pesan ini"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def _send_detailed_command(update: Update, target_date, label):
    """Logika utama untuk /besok dan /hari_ini mengirim detail."""
    preds = get_predictions_by_date(target_date, checked_status=None)

    valid_preds = [p for p in preds if "SKIP" not in p.get('bot_recommendation', '') and "NO BET" not in p.get('bot_recommendation', '')]

    if not valid_preds:
        await update.message.reply_text(f"📭 Belum ada prediksi aktif untuk {label.lower()} ({target_date} ET).")
        return

    total = len(valid_preds)
    high = sum(1 for p in valid_preds if "HIGH" in p.get('bot_confidence', ''))
    medium = sum(1 for p in valid_preds if "MEDIUM" in p.get('bot_confidence', ''))
    low = sum(1 for p in valid_preds if "LOW" in p.get('bot_confidence', ''))
    
    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d")
        day_en = dt.strftime("%A")
        day_id = HARI_MAP.get(day_en, day_en)
        date_str = f"{day_id}, {dt.strftime('%d %b %Y')} ET"
    except:
        date_str = f"{target_date} ET"
    
    msg = f"🗓️ *Prediksi {label} — {date_str}*\\n"
    msg += f"Total: {total} | 🔥 HIGH: {high} | ⚡ MEDIUM: {medium} | ⚠️ LOW: {low}\\n"
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(0.5)
    
    for pred in valid_preds:
        detail_msg = format_prediction_detail(pred, show_revision_label=False)
        markup = build_game_keyboard(
            pred['game_id'], 
            pred['user_checked'], 
            pred['away_team'], 
            pred['home_team'], 
            pred.get('game_date')
        )
        await update.message.reply_text(detail_msg, reply_markup=markup)
        await asyncio.sleep(1)
        
    await update.message.reply_text("Ketik /belum untuk detail yang belum dibeli")

async def besok_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /besok - Prediksi kalender besok ET."""
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    target_date = (now_et.date() + timedelta(days=1)).strftime("%Y-%m-%d")
    await _send_detailed_command(update, target_date, "Besok")

async def hari_ini_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /hari_ini - Prediksi hari ini ET."""
    et_tz = pytz.timezone('America/New_York')
    target_date = datetime.now(et_tz).strftime("%Y-%m-%d")
    await _send_detailed_command(update, target_date, "Hari Ini")

async def belum_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /belum."""
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    target_date = (now_et.date() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    all_preds = get_predictions_by_date(target_date, checked_status=None)
    if not all_preds:
        await update.message.reply_text(f"📭 Belum ada prediksi untuk {target_date} ET.")
        return
        
    valid_preds = [p for p in all_preds if "SKIP" not in p.get('bot_recommendation', '')]
    belum_preds = [p for p in valid_preds if p.get('user_checked') == 0]
    
    if not belum_preds:
        await update.message.reply_text("✅ Semua game besok sudah ditandai!")
        return

    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d")
        day_en = dt.strftime("%A")
        day_id = HARI_MAP.get(day_en, day_en)
        date_label = f"{day_id}, {dt.strftime('%d %b %Y')} ET"
    except:
        date_label = f"{target_date} ET"
        
    msg = f"📋 *Belum Dibeli — {date_label}*\\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\\n"
    msg += f"Total belum dibeli: {len(belum_preds)} dari {len(valid_preds)} prediksi\\n\\n"
    
    for d in belum_preds:
        seq = f"#{d['daily_sequence']}" if d.get('daily_sequence') else "#?"
        away = TEAM_SHORT_NAME.get(d.get('away_team', '???'), d.get('away_team', '???')[:12])
        home = TEAM_SHORT_NAME.get(d.get('home_team', '???'), d.get('home_team', '???')[:12])
        matchup = f"{away} @ {home}"
        
        rec = d.get('bot_recommendation', '').replace(' ✅', '').strip()
        conf = d.get('bot_confidence', '').replace(' 🔥', '').replace(' ⚡', '').strip()
        conf_emoji = "🔥" if "HIGH" in conf else "⚡" if "MEDIUM" in conf else ""
        
        line = d.get('polymarket_line', '-')
        
        msg += f"`{seq:<3} {matchup:<25}` {rec:<5} {conf_emoji:<2} | {line}\\n"
        
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\\n"
    msg += "Ketik /besok untuk semua prediksi"
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def sudah_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /sudah - Menampilkan game yang sudah ditandai 'Sudah Dibeli'."""
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    today_et = now_et.date().strftime("%Y-%m-%d")

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT * FROM predictions 
        WHERE user_checked = 1 AND is_latest = 1
        AND game_date >= ?
        ORDER BY game_date ASC, daily_sequence ASC
    """

    cursor.execute(query, (today_et,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text(f"📭 Belum ada game yang ditandai 'Sudah Beli' untuk hari ini/besok ET.")
        return

    from itertools import groupby
    rows_dict = [dict(row) for row in rows]

    response_msg = ""
    for date_val, group in groupby(rows_dict, key=lambda x: x['game_date']):
        group_list = list(group)

        try:
            dt = datetime.strptime(date_val, "%Y-%m-%d")
            day_en = dt.strftime("%A")
            day_id = HARI_MAP.get(day_en, day_en)
            date_label = f"{day_id}, {dt.strftime('%d %b %Y')} ET"
        except:
            date_label = f"{date_val} ET"

        response_msg += f"✅ *Sudah Dibeli — {date_label}*\\n"
        response_msg += "━━━━━━━━━━━━━━━━━━━━━━━━\\n"
        response_msg += f"Total dibeli: {len(group_list)} pertandingan\\n\\n"

        for d in group_list:
            seq = f"#{d['daily_sequence']}" if d.get('daily_sequence') else "#?"
            away = TEAM_SHORT_NAME.get(d.get('away_team', '???'), d.get('away_team', '???')[:12])
            home = TEAM_SHORT_NAME.get(d.get('home_team', '???'), d.get('home_team', '???')[:12])
            matchup = f"{away} @ {home}"

            checked_dt = ""
            if d.get('checked_at'):
                try:
                    dt_check = datetime.fromisoformat(d['checked_at'])
                    checked_dt = dt_check.strftime('%H:%M')
                except:
                    pass

            response_msg += f"`{seq:<3} {matchup:<25}` ✅ {checked_dt}\\n"

        response_msg += "━━━━━━━━━━━━━━━━━━━━━━━━\\n\\n"

    response_msg += "Ketik /belum untuk yang belum dibeli"
    await update.message.reply_text(response_msg, parse_mode=ParseMode.MARKDOWN)

async def akurasi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /akurasi."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            p.layer_type,
            COUNT(DISTINCT p.game_id) as total,
            SUM(CASE WHEN r.is_correct = 1 THEN 1 ELSE 0 END) as benar
        FROM predictions p
        INNER JOIN results r ON p.game_id = r.game_id
        WHERE p.is_latest = 1
        AND r.is_correct IS NOT NULL
        AND r.actual_total_runs > 0
        GROUP BY p.layer_type
        ORDER BY p.layer_type
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        await update.message.reply_text("📭 Belum ada data akurasi yang cukup.")
        return
        
    msg = "📊 *Statistik Akurasi Bot MLB*\\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\\n"
    
    total_all = 0
    benar_all = 0
    
    for r in rows:
        layer = (r['layer_type'] or "UNKNOWN").upper()
        total = r['total']
        benar = r['benar'] or 0
        pct = (benar/total*100) if total > 0 else 0
        
        emoji = "🔔" if layer == "EARLY" else "✅" if layer == "FINAL" else "🔄"
        msg += f"{emoji} {layer:<7} : {pct:.1f}% ({benar}/{total} game)\\n"
        
        total_all += total
        benar_all += benar
        
    pct_all = (benar_all/total_all*100) if total_all > 0 else 0
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\\n"
    msg += f"📈 OVERALL: {pct_all:.1f}% ({benar_all}/{total_all} game valid)\\n\\n"
    msg += "⚠️ *Catatan:* Hanya menghitung game dengan skor aktual yang valid (bukan 0-0)"
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def histori_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /histori - Menampilkan hasil prediksi terakhir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.game_date as game_date,
            p.away_team,
            p.home_team,
            p.polymarket_line,
            p.bot_recommendation,
            p.game_time_et,
            r.actual_total_runs,
            r.is_correct
        FROM predictions p
        LEFT JOIN results r ON p.game_id = r.game_id
        WHERE p.is_latest = 1
        AND p.game_date >= date('now', 'localtime', '-7 days')
        AND p.bot_recommendation NOT LIKE '%SKIP%'
        AND p.bot_recommendation NOT LIKE '%NO BET%'
        ORDER BY p.game_date DESC, p.game_time_et ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📜 Tidak ada histori ditemukan dalam 7 hari terakhir.")
        return

    from itertools import groupby
    
    msg = "📋 *Histori Prediksi — 7 Hari Terakhir*\\n\\n"
    
    rows_dict = [dict(r) for r in rows]
    total_valid = 0
    total_benar = 0

    for date_val, group in groupby(rows_dict, key=lambda x: x['game_date']):
        try:
            from datetime import datetime
            dt = datetime.strptime(date_val, "%Y-%m-%d")
            day_en = dt.strftime("%A")
            day_id = HARI_MAP.get(day_en, day_en)
            date_label = f"{day_id}, {dt.strftime('%d %b %Y')} ET"
        except:
            date_label = f"{date_val} ET"

        msg += f"━━━ {date_label} ━━━\\n"
        
        for r in group:
            away = r['away_team'][:8]
            home = r['home_team'][:8]
            line = r['polymarket_line']
            actual = r['actual_total_runs']
            rec = r['bot_recommendation'].replace(' ✅', '').replace(' ❌', '').strip()
            
            if r['is_correct'] == 1:
                status = "✅"
                res_emoji = "✅"
                total_valid += 1
                total_benar += 1
            elif r['is_correct'] == 0:
                status = "❌"
                res_emoji = "❌"
                total_valid += 1
            else:
                status = "⏳"
                res_emoji = ""
                
            actual_str = actual if actual is not None else "menunggu hasil"
            if res_emoji:
                msg += f"`{status} {away} @ {home}` | L:{line} | S:{actual_str} | {rec} {res_emoji}\\n"
            else:
                msg += f"`{status} {away} @ {home}` | L:{line} | S:{actual_str} | {rec}\\n"
                
        msg += "\\n"
        
    win_rate = (total_benar / total_valid * 100) if total_valid > 0 else 0
    msg += f"Win Rate Periode: {win_rate:.1f}% ({total_benar}/{total_valid})\\n"
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /top - 5 Prediksi HIGH confidence terkuat besok."""
    et_tz = pytz.timezone('America/New_York')
    tomorrow_et = (datetime.now(et_tz) + timedelta(days=1)).strftime("%Y-%m-%d")
    
    preds = get_predictions_by_date(tomorrow_et)
    
    top_preds = [p for p in preds if "HIGH" in p.get('bot_confidence', '') and "SKIP" not in p.get('bot_recommendation', '')]
    top_preds.sort(key=lambda p: abs(p.get('bot_expected_runs', 0) - p.get('polymarket_line', 0)), reverse=True)
    top_preds = top_preds[:5]

    if not top_preds:
        await update.message.reply_text(f"🔥 Tidak ada prediksi HIGH confidence untuk besok ({tomorrow_et} ET).")
        return

    date_str = datetime.strptime(tomorrow_et, "%Y-%m-%d").strftime("%d %b %Y")
    await update.message.reply_text(f"🔥 *TOP 5 HIGH CONFIDENCE — Besok {date_str} (ET)*", parse_mode=ParseMode.MARKDOWN)
    
    for pred in top_preds:
        msg = format_prediction_detail(pred, show_revision_label=False)
        markup = build_game_keyboard(
            pred['game_id'], 
            pred['user_checked'], 
            pred['away_team'], 
            pred['home_team'], 
            pred['game_date']
        )
        await update.message.reply_text(msg, reply_markup=markup)

async def revisi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /revisi - Perbandingan V1 vs V2 (Hari Ini & Besok)."""
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    today_et = now_et.strftime("%Y-%m-%d")
    tomorrow_et = (now_et + timedelta(days=1)).strftime("%Y-%m-%d")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(\'''
      SELECT 
        v2.game_id, v2.away_team, v2.home_team,
        v2.game_date, v2.game_time_et, v2.daily_sequence,
        v2.predicted_at,
        v1.polymarket_line as v1_line,
        v2.polymarket_line as v2_line,
        v1.bot_expected_runs as v1_expected,
        v2.bot_expected_runs as v2_expected,
        v1.bot_recommendation as v1_rec,
        v2.bot_recommendation as v2_rec,
        v1.bot_confidence as v1_conf,
        v2.bot_confidence as v2_conf,
        v2.key_factors,
        v2.user_checked
      FROM predictions v2
      JOIN predictions v1 
        ON v1.game_id = v2.game_id AND v1.version = 1
      WHERE v2.is_latest = 1
      AND v2.version > 1
      AND v2.game_date IN (?, ?)
      ORDER BY v2.game_date, v2.daily_sequence ASC, v2.game_time_et ASC
    \''', (today_et, tomorrow_et))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("✅ Tidak ada revisi prediksi untuk hari ini dan besok.")
        return

    revisi_today = []
    revisi_tomorrow = []
    seen_matchups = set()

    for r in rows:
        d = dict(r)
        matchup_key = f"{d['away_team']}_{d['home_team']}_{d['game_time_et']}_{d['game_date']}"
        
        if matchup_key in seen_matchups:
            continue
        seen_matchups.add(matchup_key)

        if d['game_date'] == today_et:
            revisi_today.append(d)
        else:
            revisi_tomorrow.append(d)

    summary_msg = f"🔄 *Daftar Revisi Prediksi (ET)*\\n"
    summary_msg += f"📅 Hari Ini: {len(revisi_today)} game\\n"
    summary_msg += f"📅 Besok  : {len(revisi_tomorrow)} game"
    await update.message.reply_text(summary_msg, parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(0.5)

    async def send_revisions(rows_list, label):
        if not rows_list:
            return
        
        await update.message.reply_text(f"━━━━━ *{label}* ━━━━━", parse_mode=ParseMode.MARKDOWN)
        
        for idx, d in enumerate(rows_list):
            seq_num = d['daily_sequence'] if d['daily_sequence'] else (idx + 1)
            seq = f"#{seq_num}"
            
            time_str = ""
            if d.get('predicted_at'):
                try:
                    dt_utc = datetime.fromisoformat(d['predicted_at'].replace('Z', '+00:00'))
                    dt_et = dt_utc.astimezone(pytz.timezone('America/New_York'))
                    time_str = f"({dt_et.strftime('%H:%M')} ET) "
                except:
                    pass

            rec_str = f"✅ Tetap {d['v2_rec']}" if d['v1_rec'] == d['v2_rec'] else f"{d['v1_rec']} → {d['v2_rec']} ⚠️ BERUBAH"
            conf_str = f"✅ Tetap {d['v2_conf']}" if d['v1_conf'] == d['v2_conf'] else f"{d['v1_conf']} → {d['v2_conf']} ⚠️ BERUBAH"
            line_str = f"✅ Tetap {d['v2_line']}" if d['v1_line'] == d['v2_line'] else f"{d['v1_line']} → {d['v2_line']}"
            
            display_date = d['game_date']
            msg = f"{seq} 🔄 REVISI {time_str}{display_date}\\n"
            msg += f"🏟️ {d['away_team']} @ {d['home_team']}\\n"
            msg += "────────────────────────────\\n"
            msg += "📊 PERUBAHAN:\\n"
            msg += f"  Line      : {line_str}\\n"
            msg += f"  Expected  : {d['v1_expected']} → {d['v2_expected']}\\n"
            msg += f"  Arah      : {rec_str}\\n"
            msg += f"  Confidence: {conf_str}\\n\\n"
            msg += "📋 KEY FACTORS TERBARU:\\n"
            msg += format_telegram_reasons(d['key_factors'])
            
            markup = build_game_keyboard(d['game_id'], d['user_checked'], d['away_team'], d['home_team'], display_date)
            await update.message.reply_text(msg, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(0.8)

    if revisi_today: await send_revisions(revisi_today, f"REVISI HARI INI ({today_et})")
    if revisi_tomorrow: await send_revisions(revisi_tomorrow, f"REVISI BESOK ({tomorrow_et})")

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Gunakan: /game [nama tim]\\nContoh: /game Yankees")
        return

    query = f"%{context.args[0]}%"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM predictions 
        WHERE (home_team LIKE ? OR away_team LIKE ?) AND is_latest = 1
        ORDER BY game_date DESC LIMIT 5
    """, (query, query))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text(f"🔍 Tidak ditemukan prediksi untuk tim '{context.args[0]}'.")
        return

    await update.message.reply_text(f"🔍 *Hasil pencarian: {context.args[0]}*", parse_mode=ParseMode.MARKDOWN)
    for pred in rows:
        pred_dict = dict(pred)
        if pred_dict.get('daily_sequence') is None:
            pred_dict['daily_sequence'] = "?"
            
        msg = format_prediction_detail(pred_dict, show_revision_label=True)
        markup = build_game_keyboard(pred_dict['game_id'], pred_dict['user_checked'], pred_dict['away_team'], pred_dict['home_team'], pred_dict['game_date'])
        await update.message.reply_text(msg, reply_markup=markup)

async def prediksi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /prediksi - Menganalisis ulang semua game mendatang secara on-demand."""
    await update.message.reply_text("⏳ *Sedang mengambil data terbaru dari Polymarket...*\\nProses analisis dimulai. Hasil akan dikirimkan satu per satu.", parse_mode=ParseMode.MARKDOWN)
    
    try:
        games = get_upcoming_games()
        if not games:
            await update.message.reply_text("📭 Tidak ada jadwal pertandingan mendatang untuk dianalisis.")
            return

        now_utc = datetime.now(pytz.UTC)
        upcoming_games = []
        for g in games:
            try:
                game_time = datetime.fromisoformat(g['game_time'].replace('Z', '+00:00'))
                if game_time > now_utc:
                    upcoming_games.append(g)
            except:
                upcoming_games.append(g)

        if not upcoming_games:
            await update.message.reply_text("📭 Semua pertandingan hari ini sudah dimulai.")
            return

        analyzed_count = 0
        for game in upcoming_games:
            home_team = game['home_team']
            away_team = game['away_team']
            game_id = str(game['game_id'])

            market_info = get_ou_line(home_team, away_team)
            if not market_info: continue

            try:
                pitchers = get_starting_pitchers(game_id)
                home_p_id = pitchers['home']['id'] if pitchers['home'] else None
                away_p_id = pitchers['away']['id'] if pitchers['away'] else None
                
                game_full_data = {
                    "home_team_id": game.get('home_id'),
                    "home_team_stats": get_team_season_offense(game.get('home_id')),
                    "away_team_stats": get_team_season_offense(game.get('away_id')),
                    "home_pitcher_stats": get_pitcher_season_stats(home_p_id),
                    "away_pitcher_stats": get_pitcher_season_stats(away_p_id),
                    "home_pitcher_last_3": get_pitcher_last_3_starts(home_p_id),
                    "away_pitcher_last_3": get_pitcher_last_3_starts(away_p_id),
                    "home_bullpen_era": get_bullpen_era(game.get('home_id')),
                    "away_bullpen_era": get_bullpen_era(game.get('away_id')),
                    "home_streak": calculate_streak(get_team_last_10_games(game.get('home_id'))),
                    "away_streak": calculate_streak(get_team_last_10_games(game.get('away_id'))),
                    "weather": get_game_weather(game['venue_name'], game['game_time']),
                    "park_factor": get_park_factor(game.get('home_id'))
                }
                
                analysis = calculate_expected_total_runs(game_full_data)
                analysis["recommendation"] = make_recommendation(analysis["final_expected_runs"], market_info['line'])
                analysis["confidence"] = calculate_confidence(analysis["final_expected_runs"], market_info['line'])
                analysis['layer_type'] = 'manual'

                game_info = game.copy()
                game_info['polymarket_line'] = market_info['line']
                game_info['game_time_et'] = market_info.get('game_time_et', 'N/A')
                game_info['game_date'] = market_info.get('game_date_et')
                game_info['line_range'] = market_info.get('line_range', '-')
                game_info['raw_stats'] = game_full_data

                save_prediction(game_info, analysis)
                
                latest = get_latest_prediction(game_id)
                if latest:
                    msg = format_prediction_detail(latest, show_revision_label=True)
                    markup = build_game_keyboard(game_id, latest['user_checked'], latest['away_team'], latest['home_team'], latest['game_date'])
                    await update.message.reply_text(msg, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
                    analyzed_count += 1
                
                await asyncio.sleep(1.5)

            except Exception as e:
                logger.error(f"Error menganalisis game {game_id}: {e}")
                continue

        if analyzed_count == 0:
            await update.message.reply_text("📭 Tidak ada data market baru yang ditemukan untuk dianalisis.")
        else:
            await update.message.reply_text(f"✅ Analisis selesai. {analyzed_count} pertandingan diperbarui.")

    except Exception as e:
        logger.error(f"Error pada /prediksi: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan saat menjalankan analisis.")

async def layer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /layer [nomor] - Menampilkan history layer."""
    if not context.args:
        await update.message.reply_text("Gunakan: /layer [nomor]\\nContoh: /layer 1")
        return

    seq = context.args[0]
    et_tz = pytz.timezone('America/New_York')
    today = datetime.now(et_tz).date().strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM predictions 
        WHERE daily_sequence = ? AND game_date = ?
        ORDER BY version ASC
    """, (seq, today))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text(f"❌ Tidak ditemukan data game #{seq} untuk hari ini (ET).")
        return

    first = rows[0]
    msg = f"🔍 *History Layer Game #{seq}*\\n"
    msg += f"🏟️ {first['away_team']} @ {first['home_team']}\\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
    
    for i, r in enumerate(rows):
        l_type = r['layer_type'] or f"V{r['version']}"
        l_type = l_type.upper()
        
        sent_at = ""
        if r['layer_sent_at']:
            try:
                dt_utc = datetime.fromisoformat(r['layer_sent_at'].replace('Z', '+00:00'))
                dt_et = dt_utc.astimezone(pytz.timezone('America/New_York'))
                sent_at = f"({dt_et.strftime('%H:%M')} ET)"
            except:
                pass
                
        msg += f"📍 *{l_type}* {sent_at}:\\n"
        msg += f"   Expected: {r['bot_expected_runs']} | {r['bot_recommendation']} | {r['bot_confidence']}\\n"
        
        if i > 0:
            prev = rows[i-1]
            diff_exp = r['bot_expected_runs'] - prev['bot_expected_runs']
            trend = "⬆️ NAIK" if diff_exp > 0 else "⬇️ TURUN" if diff_exp < 0 else "✅ SAMA"
            msg += f"   vs Prev: {trend} ({diff_exp:+.1f})\\n"
        msg += "\\n"

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def setline_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /setline [nomor] [line] - Update line manual (backup)."""
    if len(context.args) < 2:
        await update.message.reply_text("Gunakan: /setline [nomor] [line]\\nContoh: /setline 1 10.5")
        return

    seq = context.args[0]
    new_line = context.args[1]
    et_tz = pytz.timezone('America/New_York')
    today = datetime.now(et_tz).date().strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE predictions SET polymarket_line = ? WHERE daily_sequence = ? AND game_date = ? AND is_latest = 1", (new_line, seq, today))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Line untuk game #{seq} berhasil diupdate ke {new_line}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data.startswith("check_") or data.startswith("uncheck_"):
        is_checking = data.startswith("check_")
        game_id = data.replace("check_", "") if is_checking else data.replace("uncheck_", "")
        
        new_status = 1 if is_checking else 0
        from datetime import datetime
        now_str = datetime.now().isoformat() if is_checking else None
        
        conn = get_db_connection()
        conn.execute(
            "UPDATE predictions SET user_checked = ?, checked_at = ? WHERE game_id = ?",
            (new_status, now_str, game_id)
        )
        conn.commit()
        
        row = conn.execute("SELECT * FROM predictions WHERE game_id = ? AND is_latest = 1", (game_id,)).fetchone()
        conn.close()
        
        if row:
            row_dict = dict(row)
            try:
                markup = build_game_keyboard(
                    game_id,
                    new_status,
                    row_dict['away_team'],
                    row_dict['home_team'],
                    row_dict['game_date']
                )
                
                current_text = query.message.text
                if "📋 KEY FACTORS" in current_text:
                    new_text = format_prediction_detail(row_dict, show_revision_label=("REVISI" in current_text))
                    await query.edit_message_text(text=new_text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
                else:
                    await query.edit_message_reply_markup(reply_markup=markup)
            except Exception as e:
                if "Message is not modified" not in str(e):
                    print(f"[Callback Error] {e}")
                
        status_text = "Telah ditandai sebagai Sudah Dibeli!" if is_checking else "Tanda Sudah Dibeli dibatalkan."
        await query.answer(status_text)

def run_bot_listener():
    """Fungsi utama untuk menjalankan bot listener Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN tidak ditemukan di .env. Bot tidak dapat dijalankan.")
        return
        
    logger.info("Menjalankan bot listener Telegram...")
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("prediksi", prediksi_command))
    app.add_handler(CommandHandler("besok", besok_command))
    app.add_handler(CommandHandler("hari_ini", hari_ini_command))
    app.add_handler(CommandHandler("belum", belum_command))
    app.add_handler(CommandHandler("sudah", sudah_command))
    app.add_handler(CommandHandler("akurasi", akurasi_command))
    app.add_handler(CommandHandler("revisi", revisi_command))
    app.add_handler(CommandHandler("histori", histori_command))
    app.add_handler(CommandHandler("game", game_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("layer", layer_command))
    app.add_handler(CommandHandler("setline", setline_command))
    
    # Register callback handler
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Start polling
    app.run_polling()
'''

with open('src/output/telegram_bot.py', 'w') as f:
    f.write(content)
