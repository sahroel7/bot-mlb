"""
Modul Integrasi Discord (Phase 2 Enhancement).
Digunakan untuk mengirim alert analisis dan ringkasan harian via Webhook.

--- CARA SETUP DISCORD WEBHOOK ---
1. Buka server Discord Anda -> Server Settings -> Integrations -> Webhooks
2. Klik "New Webhook", beri nama (misal: MLB AI Bot), dan pilih channel
3. Klik "Copy Webhook URL"
4. Masukkan URL tersebut ke file .env sebagai DISCORD_WEBHOOK_URL
----------------------------------
"""

import os
import time
import requests
from dotenv import load_dotenv
from datetime import datetime
from src.utils.logger import logger

# Load environment variables
load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def format_discord_reasons(reasons):
    """Memformat list reasons menjadi string dengan emoji."""
    if not reasons:
        return "➖ Semua metrik dalam batas rata-rata"
        
    formatted = []
    for reason in reasons:
        emoji = "•"
        if "Pitcher" in reason or "ERA" in reason or "K/9" in reason:
            emoji = "⚾"
        elif "Suhu" in reason or "Angin" in reason or "Cuaca" in reason:
            emoji = "🌡️"
        elif "Park" in reason or "Field" in reason:
            emoji = "🏟️"
        elif "Offense" in reason or "Streak" in reason or "RISP" in reason or "Momentum" in reason:
            emoji = "💪"
        elif "Nilai" in reason:
            emoji = "⚠️"
            
        formatted.append(f"{emoji} {reason}")
    return "\n".join(formatted)

def send_with_retry(payload, retries=3):
    """Mengirim payload ke Discord dengan penanganan rate limit (429)."""
    if not DISCORD_WEBHOOK_URL:
        logger.warning("[Discord] Webhook URL belum disetel di .env. Skip pengiriman.")
        return False
        
    for attempt in range(retries):
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            
            if response.status_code in [200, 204]:
                return True
            elif response.status_code == 429:
                # Rate limited
                retry_after = response.json().get('retry_after', 2.0)
                logger.warning(f"[Discord] Rate limited. Menunggu {retry_after} detik...")
                time.sleep(retry_after)
            else:
                logger.error(f"[Discord Error] Gagal mengirim pesan. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"[Discord Error] Percobaan {attempt+1} gagal: {e}")
            time.sleep(2)
            
    return False

def send_game_analysis_embed(game_info, analysis_result):
    """
    Mengirim hasil analisis game spesifik sebagai Discord Embed.
    """
    matchup = f"{game_info['away_team']} @ {game_info['home_team']}"
    
    # Set warna berdasarkan rekomendasi
    rec = analysis_result.get("recommendation", "SKIP")
    color = 16766720 # Kuning (Default/SKIP)
    if "OVER" in rec:
        color = 3066993 # Hijau
    elif "UNDER" in rec:
        color = 3447003 # Biru
        
    conf = analysis_result.get("confidence", "LOW")
    reasons_text = format_discord_reasons(analysis_result.get("reasons", []))
    
    embed = {
        "title": f"🏟️ {matchup}",
        "description": f"Pertandingan: {game_info.get('game_time', '')[:10]}",
        "color": color,
        "fields": [
            {
                "name": "📊 Polymarket Line",
                "value": f"**{game_info.get('polymarket_line', 'N/A')}**",
                "inline": True
            },
            {
                "name": "🎯 Expected Runs",
                "value": f"**{analysis_result.get('final_expected_runs', 'N/A')}**",
                "inline": True
            },
            {
                "name": "📈 Recommendation",
                "value": f"**{rec}**",
                "inline": True
            },
            {
                "name": "🔥 Confidence",
                "value": f"**{conf}**",
                "inline": True
            },
            {
                "name": "📋 Key Factors",
                "value": reasons_text,
                "inline": False
            }
        ],
        "footer": {
            "text": f"MLB AI Bot | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    }
    
    payload = {
        "embeds": [embed]
    }
    
    return send_with_retry(payload)

def send_alert_embed(game_info, analysis_result):
    """
    Format khusus untuk alert HIGH confidence yang lebih mencolok.
    Bisa dipanggil oleh alert_system.py.
    """
    # Untuk sementara kita gunakan format yang sama, bisa ditambahkan ping role nantinya
    return send_game_analysis_embed(game_info, analysis_result)

def send_daily_summary_embed(all_analyses):
    """
    Mengirim ringkasan seluruh game hari ini dalam satu pesan/embed.
    """
    if not all_analyses:
        return
        
    description = ""
    has_high_confidence = False
    
    for item in all_analyses:
        game = item['game_info']
        ans = item['analysis']
        
        matchup = f"{game['away_team']} @ {game['home_team']}"
        rec = ans['recommendation']
        conf = ans['confidence']
        line = game.get('polymarket_line', '-')
        proj = ans['final_expected_runs']
        
        # Tambahkan emoji api untuk game target utama
        prefix = "🔥 " if "HIGH" in conf else "➖ "
        if "HIGH" in conf: has_high_confidence = True
            
        description += f"{prefix}**{matchup}**\n"
        description += f"└ Line: {line} | Proj: {proj} | **{rec}**\n\n"
        
    if has_high_confidence:
        description += "\n💡 *Terdapat edge kuat (HIGH) hari ini. Cek pesan detail di atas!*"
    else:
        description += "\n⚠️ *Tidak ada edge yang sangat kuat hari ini. Gunakan stakes yang aman.*"
        
    embed = {
        "title": "⚾ MLB AI BOT DAILY SUMMARY ⚾",
        "description": description,
        "color": 15158332 if has_high_confidence else 9807270, # Merah/Abu-abu
        "footer": {
            "text": f"MLB AI Bot | {datetime.now().strftime('%Y-%m-%d')}"
        }
    }
    
    payload = {
        "embeds": [embed]
    }
    
    return send_with_retry(payload)
