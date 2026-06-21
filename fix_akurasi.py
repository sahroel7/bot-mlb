import re

with open('src/output/telegram_bot.py', 'r') as f:
    content = f.read()

# Fix akurasi_command
old_func = re.search(r'async def akurasi_command\(update: Update, context: ContextTypes.DEFAULT_TYPE\):.*?(?=async def |\Z)', content, re.DOTALL)
if old_func:
    new_func = '''async def akurasi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

'''
    content = content.replace(old_func.group(0), new_func)
    
    with open('src/output/telegram_bot.py', 'w') as f:
        f.write(content)
