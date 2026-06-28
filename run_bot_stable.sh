#!/bin/bash
# run_bot_stable.sh
# Script untuk menjalankan MLB Bot dengan auto-restart jika crash.

VENV_PATH="./venv/bin/python3"
BOT_SCRIPT="run_bot.py"

echo "━" * 60
echo "🚀 MLB AI Bot Stable Runner Started"
echo "━" * 60

while true; do
  echo "[$(date)] Memulai bot..."
  $VENV_PATH $BOT_SCRIPT
  
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date)] Bot dimatikan secara normal. Berhenti."
    break
  else
    echo "[$(date)] Bot crash dengan exit code $EXIT_CODE. Restart dalam 10 detik..."
    sleep 10
  fi
done
