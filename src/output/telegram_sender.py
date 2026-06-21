"""
Modul Integrasi Telegram (Phase 2 Enhancement).
Digunakan untuk mengirim alert analisis dan ringkasan harian secara otomatis.
"""

import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from src.utils.logger import logger
from src.utils.bullpen_url_generator import generate_bullpen_url

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_async_message(text, reply_markup=None):
    """Fungsi helper asinkron untuk mengirim pesan dengan retry logic."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("[Telegram] Token atau Chat ID belum disetel di .env. Skip pengiriman.")
        return False
        
    retries = 3
    delay = 5
    timeout = 30
    
    for attempt in range(retries):
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                read_timeout=timeout,
                write_timeout=timeout,
                connect_timeout=timeout
            )
            logger.info(f"[Telegram] Pesan berhasil dikirim ke {TELEGRAM_CHAT_ID}")
            return True
        except Exception as e:
            if attempt < retries - 1:
                logger.warning(f"[Telegram Warning] Percobaan {attempt+1} gagal: {e}. Mengulang dalam {delay} detik...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"[Telegram Error] Gagal mengirim pesan setelah {retries} percobaan: {e}")
                return False

def format_telegram_reasons(reasons):
    """Memformat list reasons menjadi list bermarkdown dengan emoji."""
    if not reasons:
        return ""
        
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
    return "\n".join(formatted)

def get_time_period_label(wib_time_str):
    """Memberikan label periode berdasarkan waktu WIB (HH:MM WIB)."""
    try:
        hour = int(wib_time_str.split(":")[0])
        if 0 <= hour <= 5:
            return "(dini hari)"
        elif 6 <= hour <= 11:
            return "(pagi)"
        elif 12 <= hour <= 17:
            return "(siang)"
        else:
            return "(malam)"
    except:
        return ""

def _normalize_data(game_info, analysis_result=None):
    """Menyeragamkan format data dari main bot maupun dari database."""
    if analysis_result is None:
        item = game_info
        reasons = []
        if 'key_factors' in item and item['key_factors']:
            try:
                reasons = json.loads(item['key_factors'])
            except:
                reasons = []
        
        return {
            'game_id': item.get('game_id', 'Unknown'),
            'away': item.get('away_team', 'Unknown'),
            'home': item.get('home_team', 'Unknown'),
            'time': item.get('game_date', ''),
            'game_date_et': item.get('game_date', ''),
            'game_date_wib': item.get('game_date_wib', ''),
            'game_time_et': item.get('game_time_et', 'N/A'),
            'game_time_wib': item.get('game_time_wib', 'N/A'),
            'line': item.get('polymarket_line', '-'),
            'line_range': item.get('line_range', '-'),
            'expected': item.get('bot_expected_runs', 0),
            'rec': item.get('bot_recommendation', 'SKIP'),
            'conf': item.get('bot_confidence', 'LOW'),
            'source': 'Database',
            'reasons': reasons,
            'user_checked': item.get('user_checked', 0),
            'checked_at': item.get('checked_at', None),
            'version': item.get('version', 1),
            'seq': item.get('daily_sequence', None),
            'layer_type': item.get('layer_type', None)
        }
    else:
        return {
            'game_id': game_info.get('game_id', 'Unknown'),
            'away': game_info.get('away_team', 'Unknown'),
            'home': game_info.get('home_team', 'Unknown'),
            'time': game_info.get('game_time', '')[:10],
            'game_date_et': game_info.get('game_date_et'),
            'game_date_wib': game_info.get('game_date_wib'),
            'game_time_et': game_info.get('game_time_et', 'N/A'),
            'game_time_wib': game_info.get('game_time_wib', 'N/A'),
            'line': game_info.get('polymarket_line', '-'),
            'line_range': game_info.get('line_range', '-'),
            'expected': analysis_result.get('final_expected_runs', 0),
            'rec': analysis_result.get('recommendation', 'SKIP'),
            'conf': analysis_result.get('confidence', 'LOW'),
            'source': game_info.get('odds_source', 'N/A'),
            'reasons': analysis_result.get('reasons', []),
            'user_checked': 0,
            'checked_at': None,
            'version': 1,
            'seq': None,
            'layer_type': analysis_result.get('layer_type', None)
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

def _build_game_message(data):
    """Membangun teks pesan dan markup untuk satu game."""
    matchup = f"{data['away']} @ {data['home']}"
    seq_str = f"#{data['seq']} " if data['seq'] else ""
    
    layer_label = ""
    if data.get('layer_type') == 'early':
        layer_label = "🔔 EARLY ALERT — "
    elif data.get('layer_type') == 'final':
        layer_label = "✅ FINAL ALERT — "
    elif data.get('layer_type') == 'revision' or data.get('version', 1) > 1:
        layer_label = "🔄 REVISI — "
    
    # Prioritaskan game_date_wib (WIB Date)
    raw_date = data.get('game_date_wib') or data.get('game_date_et') or data['time']
    try:
        dt = datetime.strptime(raw_date, "%Y-%m-%d")
        day_en = dt.strftime("%A")
        day_id = HARI_MAP.get(day_en, day_en)
        date_str = f"{day_id}, {dt.strftime('%d %b %Y')}"
    except:
        date_str = raw_date
        
    wib_time = data.get('game_time_wib', 'N/A')
    line_range = data.get('line_range', data['line'])
    
    msg = f"{seq_str}{layer_label}🏟️ *{matchup}*\n"
    msg += f"📅 {date_str} | ⏰ {wib_time}\n"
    msg += f"────────────────────────────\n"
    msg += f"📊 Line Analisis : *{data['line']}*\n"
    msg += f"📏 Rentang Line  : *{line_range}*\n"
    msg += f"🎯 Expected      : *{data['expected']}*\n"
    msg += f"📈 Arah          : *{data['rec']}*\n"
    msg += f"🔥 Conf          : *{data['conf']}*\n"
    
    if data.get('layer_type') == 'early':
        msg += f"⚠️ Status : Early Alert\n"
    
    msg += f"📡 Sumber : {data['source']}\n\n"
    
    if data['reasons']:
        msg += f"📋 *KEY FACTORS:*\n"
        msg += format_telegram_reasons(data['reasons']) + "\n"
    
    buttons = []
    if "HIGH" in data['conf'] or "MEDIUM" in data['conf']:
        game_url = generate_bullpen_url(data['away'], data['home'], data['time'])
        buttons.append([InlineKeyboardButton("💰 Buka Bullpen.fi", url=game_url)])
    
    if data['user_checked']:
        time_str = ""
        if data['checked_at']:
            try:
                dt = datetime.fromisoformat(data['checked_at'])
                time_str = f" - {dt.strftime('%H:%M')}"
            except:
                pass
        buttons.append([InlineKeyboardButton(f"✅ Sudah Dibeli{time_str} | 🔄 Batalkan", callback_data=f"uncheck_{data['game_id']}")])
    else:
        buttons.append([InlineKeyboardButton("☑️ Tandai Sudah Beli", callback_data=f"check_{data['game_id']}")])
        
    reply_markup = InlineKeyboardMarkup(buttons)
    return msg, reply_markup

def send_game_analysis(game_info, analysis_result):
    """Mengirim hasil analisis tunggal."""
    data = _normalize_data(game_info, analysis_result)
    if "LOW" in data['conf'] or "SKIP" in data['rec']:
        return
    msg, reply_markup = _build_game_message(data)
    asyncio.run(send_async_message(msg, reply_markup))

async def _send_summary_sequence(all_analyses, waiting_games=None):
    """Worker asinkron untuk mengirim urutan summary dengan delay."""
    if not all_analyses and not waiting_games:
        return

    normalized_list = []
    for item in all_analyses:
        if isinstance(item, dict) and 'game_info' in item:
            normalized_list.append(_normalize_data(item['game_info'], item['analysis']))
        else:
            normalized_list.append(_normalize_data(item))

    # Filter: Hanya MEDIUM dan HIGH
    targets = [d for d in normalized_list if "SKIP" not in d['rec'] and "LOW" not in d['conf']]
    
    high_count = sum(1 for d in targets if "HIGH" in d['conf'])
    med_count = sum(1 for d in targets if "MEDIUM" in d['conf'])
    today_str = datetime.now().strftime("%d %b %Y")

    # 1. Pesan Pembuka
    header = f"🏟️ *MLB Predictions — {today_str}*\n"
    header += f"📊 Total: {len(targets)} game | 🔥 HIGH: {high_count} | ⚡ MEDIUM: {med_count}\n"
    header += f"─────────────────────"
    await send_async_message(header)
    await asyncio.sleep(2)

    # 2. Pesan Per Game
    for data in targets:
        msg, reply_markup = _build_game_message(data)
        await send_async_message(msg, reply_markup)
        await asyncio.sleep(2)

    # 3. Pesan Waiting Markets
    if waiting_games:
        wait_msg = "⏳ *MENUNGGU MARKET TERBUKA:*\n"
        for g in waiting_games:
            wait_msg += f"• {g['away_team']} @ {g['home_team']}\n"
        wait_msg += "\nBot akan kirim alert otomatis saat market buka."
        await send_async_message(wait_msg)
        await asyncio.sleep(2)

    # 4. Pesan Penutup
    footer = "✅ *Semua prediksi hari ini sudah dikirim.*\n"
    footer += "💾 Tersimpan di database untuk evaluasi akurasi."
    await send_async_message(footer)

def send_daily_summary(all_analyses, waiting_games=None):
    """Entry point untuk mengirim ringkasan harian."""
    asyncio.run(_send_summary_sequence(all_analyses, waiting_games))

def send_daily_results(rows, date_str):
    """
    Mengirim laporan hasil pertandingan kemarin ke Telegram.
    """
    if not rows:
        return

    correct = sum(1 for r in rows if r[7] == 1)
    incorrect = sum(1 for r in rows if r[7] == 0)
    win_rate = (correct / (correct + incorrect) * 100) if (correct + incorrect) > 0 else 0
    
    msg = f"📊 *Laporan Hasil MLB — {date_str}*\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"✅ Benar: {correct} | ❌ Salah: {incorrect}\n"
    msg += f"📈 *Win Rate: {win_rate:.1f}%*\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for r in rows:
        away, home, g_date, line, rec, conf, actual, is_correct = r
        status = "✅" if is_correct == 1 else "❌" if is_correct == 0 else "⏳" if actual is not None else "🕒"
        matchup = f"{away[:10]} @ {home[:10]}"
        msg += f"{status} `{matchup:<20}` | L:{line} | S:{actual if actual is not None else '-'}\n"

    asyncio.run(send_async_message(msg))

def send_test_message():
    """Mengirim pesan percobaan untuk verifikasi koneksi."""
    msg = "✅ MLB AI Bot terhubung! Kamu akan menerima prediksi di sini."
    asyncio.run(send_async_message(msg))
