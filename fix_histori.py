import re

with open('src/output/telegram_bot.py', 'r') as f:
    content = f.read()

old_func = re.search(r'async def histori_command\(update: Update, context: ContextTypes.DEFAULT_TYPE\):.*?(?=async def |\Z)', content, re.DOTALL)
if old_func:
    new_func = '''async def histori_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /histori - Menampilkan hasil prediksi terakhir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.game_date_et as game_date,
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
        AND p.game_date_et >= date('now', 'localtime', '-7 days')
        AND p.bot_recommendation NOT LIKE '%SKIP%'
        AND p.bot_recommendation NOT LIKE '%NO BET%'
        ORDER BY p.game_date_et DESC, p.game_time_et ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📜 Tidak ada histori ditemukan dalam 7 hari terakhir.")
        return

    from itertools import groupby
    
    HARI_MAP = {
        "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
        "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
    }

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

'''
    content = content.replace(old_func.group(0), new_func)
    
    with open('src/output/telegram_bot.py', 'w') as f:
        f.write(content)
