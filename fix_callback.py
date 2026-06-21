import re

with open('src/output/telegram_bot.py', 'r') as f:
    content = f.read()

# Fix handle_callback
old_func = re.search(r'async def handle_callback\(update: Update, context: ContextTypes.DEFAULT_TYPE\):.*?(?=async def |\Z)', content, re.DOTALL)
if old_func:
    new_func = '''async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
'''
    content = content.replace(old_func.group(0), new_func)
    
    with open('src/output/telegram_bot.py', 'w') as f:
        f.write(content)
