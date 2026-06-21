import json
import glob

# Try to find a backup of telegram_bot.py from the read_file outputs
files = glob.glob('/home/piyuk/.gemini/tmp/bot-mlb/tool-outputs/session-a5ddea35-2288-4dc2-a9fa-586c99cd677b/read_file_*.txt')

for fpath in files:
    try:
        with open(fpath, 'r') as f:
            data = json.load(f)
            output = data.get('output', '')
            if 'async def handle_callback' in output and 'def run_bot_listener' in output:
                print(f"Found match in {fpath}")
                # We can't fully restore from these because they were truncated.
    except Exception as e:
        pass
