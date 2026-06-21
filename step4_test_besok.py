import asyncio
import sqlite3
from datetime import date, timedelta
from src.output.telegram_bot import get_predictions_by_date, format_prediction_detail

target_date = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
preds = get_predictions_by_date(target_date)

valid_preds = [p for p in preds if not ("SKIP" in p.get('bot_recommendation', '') or "LOW" in p.get('bot_confidence', ''))]

print(f"🗓️ Prediksi Besok — {target_date}")
print(f"Total valid to send (not SKIP/LOW): {len(valid_preds)}")
print("=" * 40)

for pred in valid_preds:
    print(format_prediction_detail(pred, show_revision_label=True))
    print("----------------------------------------")
