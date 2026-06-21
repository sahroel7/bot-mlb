import re

with open('src/database/prediction_tracker.py', 'r') as f:
    content = f.read()

# Hapus baris yang assign variabel wib
content = re.sub(r"^\s*game_time_wib\s*=\s*game_info.*?\n", "", content, flags=re.MULTILINE)
content = re.sub(r"^\s*game_date_wib\s*=\s*game_info.*?\n", "", content, flags=re.MULTILINE)

# Hapus dari VALUES / UPDATE query tuple
content = content.replace("line_range, game_date_wib, game_id, game_time_et", "line_range, game_id, game_time_et")
content = content.replace("if not game_date_wib: game_date_wib = existing['game_date_wib']\n", "")

# Fix logic target_date_for_seq
content = re.sub(r"# Jika game_date_wib belum.*?\n\s*target_date_for_seq =.*?\n", "            target_date_for_seq = game_date\n", content, flags=re.MULTILINE)

content = content.replace("WHERE (game_date_wib = ? OR (game_date_wib IS NULL AND game_date = ?))", "WHERE game_date = ?")
content = content.replace("(target_date_for_seq, target_date_for_seq)", "(target_date_for_seq,)")

content = content.replace("game_time_wib, game_date_wib, ", "")
content = content.replace("game_time_wib, game_date_wib", "")

with open('src/database/prediction_tracker.py', 'w') as f:
    f.write(content)
