"""
Modul Health Check (Phase 4 Reliability).
Melakukan verifikasi sistem sebelum bot memulai proses analisis.
"""

import requests
import sqlite3
import os
import asyncio
from colorama import Fore, Style, init

from config.config_loader import load_config
from src.database.db_setup import DB_PATH
from dotenv import load_dotenv

load_dotenv()
init(autoreset=True)

def check_mlb_api():
    """Ping MLB Stats API."""
    url = "https://statsapi.mlb.com/api/v1/sports"
    try:
        r = requests.get(url, timeout=5)
        return r.status_code == 200, None
    except Exception as e:
        return False, str(e)

def check_polymarket_api():
    """Ping Polymarket API."""
    url = "https://clob.polymarket.com/markets"
    try:
        r = requests.get(url, timeout=5)
        return r.status_code in [200, 204], None
    except Exception as e:
        return False, str(e)

def check_weather_api():
    """Ping Open-Meteo API (Gunakan lokasi dummy)."""
    url = "https://api.open-meteo.com/v1/forecast?latitude=40.71&longitude=-74.00&current_weather=true"
    try:
        r = requests.get(url, timeout=5)
        return r.status_code == 200, None
    except Exception as e:
        return False, str(e)

def check_database():
    """Verifikasi read/write SQLite."""
    if not os.path.exists(DB_PATH):
        return False, "File database tidak ditemukan."
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS _health_check (id INTEGER)")
        cursor.execute("INSERT INTO _health_check VALUES (1)")
        cursor.execute("DELETE FROM _health_check")
        conn.commit()
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

def check_config():
    """Verifikasi file settings.yaml."""
    try:
        cfg = load_config()
        if not cfg or "confidence_thresholds" not in cfg:
            return False, "Struktur config tidak valid atau file hilang."
        return True, None
    except Exception as e:
        return False, str(e)

def check_telegram():
    """Verifikasi konfigurasi Telegram (Opsional)."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id or token == "your_telegram_bot_token_here":
        return False, "Not configured (optional)"
        
    # Test validitas token via getMe
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return True, None
        else:
            return False, "Invalid Token"
    except Exception as e:
        return False, str(e)

def run_health_check():
    """
    Menjalankan semua pengecekan sistem.
    Returns:
        bool: True jika sistem siap jalan, False jika ada Critical Error.
    """
    print(f"\n{Fore.CYAN}{Style.BRIGHT}=== SYSTEM HEALTH CHECK ===")
    
    checks = {
        "MLB Stats API": check_mlb_api,
        "Polymarket API": check_polymarket_api,
        "Weather API": check_weather_api,
        "Database": check_database,
        "Configuration": check_config,
        "Telegram (Alerts)": check_telegram
    }
    
    critical_errors = []
    weather_down = False
    
    for name, func in checks.items():
        is_ok, err_msg = func()
        
        if is_ok:
            print(f"{Fore.GREEN}✅ {name:<18} — OK")
        else:
            if name in ["MLB Stats API", "Polymarket API", "Database", "Configuration"]:
                print(f"{Fore.RED}❌ {name:<18} — FAILED: {err_msg}")
                critical_errors.append(name)
            elif name == "Weather API":
                print(f"{Fore.YELLOW}⚠️ {name:<18} — WARNING: {err_msg} (Bot akan lanjut tanpa modifier cuaca)")
                weather_down = True
            else: # Telegram opsional
                print(f"{Fore.YELLOW}⚠️ {name:<18} — {err_msg}")
                
    print(f"{Fore.CYAN}{Style.BRIGHT}===========================\n")
    
    if critical_errors:
        print(f"{Fore.RED}{Style.BRIGHT}[CRITICAL ERROR] Bot dihentikan karena komponen berikut gagal: {', '.join(critical_errors)}")
        return False
        
    return True

if __name__ == "__main__":
    run_health_check()