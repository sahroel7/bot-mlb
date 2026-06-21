import json

# This script will extract the file content from the read_file output
try:
    with open('/home/piyuk/.gemini/tmp/bot-mlb/tool-outputs/session-a5ddea35-2288-4dc2-a9fa-586c99cd677b/read_file_read_file__read_file_1781715831438_0_q6dwm7.txt', 'r') as f:
        data = json.load(f)
        output = data.get('output', '')
        
        # Extract everything after "--- FILE CONTENT (truncated) ---\n"
        parts = output.split("--- FILE CONTENT (truncated) ---\n")
        if len(parts) > 1:
            content = parts[1]
            print(f"Extracted {len(content)} chars")
            
            # Since this is a truncated read, we can't restore the whole file from it.
            # We need to look elsewhere.
except Exception as e:
    print(f"Error reading file: {e}")
