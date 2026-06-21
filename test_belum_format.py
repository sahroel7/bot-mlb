import asyncio
from datetime import datetime, timedelta
from src.output.telegram_bot import get_predictions_by_date, format_prediction_ringkas, TEAM_SHORT_NAME

target_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
preds = get_predictions_by_date(target_date)
valid_preds = [p for p in preds if not ('SKIP' in p.get('bot_recommendation', '') or 'LOW' in p.get('bot_confidence', ''))]

msg = f'📋 *Belum Dibeli — {target_date}*\n━━━━━━━━━━━━━━━━━━━━━━━━\nTotal belum dibeli: {len(valid_preds)} dari {len(valid_preds)} prediksi\n\n'

for d in valid_preds[:3]:
    seq = f"#{d['daily_sequence']}" if d.get('daily_sequence') else "#?"
    away = TEAM_SHORT_NAME.get(d['away_team'], d['away_team'][:12])
    home = TEAM_SHORT_NAME.get(d['home_team'], d['home_team'][:12])
    matchup = f"{away} @ {home}"
    
    rec = d.get('bot_recommendation', '').replace(' ✅', '').strip()
    conf = d.get('bot_confidence', '').replace(' 🔥', '').replace(' ⚡', '').strip()
    conf_emoji = '🔥' if 'HIGH' in conf else '⚡' if 'MEDIUM' in conf else ''
    
    line = d.get('polymarket_line', '-')
    
    msg += f"`{seq:<3} {matchup:<25}` {rec:<5} {conf_emoji:<2} | {line}\n"
    
print(msg)
