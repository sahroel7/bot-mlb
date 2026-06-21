"""
Loader Konfigurasi.
Bertugas membaca settings.yaml dan menyediakan nilai default fallback.
"""

import os
import yaml

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'settings.yaml'))

_CONFIG_CACHE = None

def load_config():
    """Membaca file YAML ke dalam memory."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
        
    if not os.path.exists(CONFIG_PATH):
        print(f"[Warning] File konfigurasi tidak ditemukan di {CONFIG_PATH}. Menggunakan fallback.")
        _CONFIG_CACHE = {}
        return _CONFIG_CACHE
        
    try:
        with open(CONFIG_PATH, 'r') as f:
            _CONFIG_CACHE = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[Error] Gagal membaca konfigurasi: {e}")
        _CONFIG_CACHE = {}
        
    return _CONFIG_CACHE

def get_setting(key_path, default_value=None):
    """
    Mengambil nilai setting berdasarkan key path (misal: 'confidence_thresholds.high_gap').
    """
    config = load_config()
    keys = key_path.split('.')
    
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default_value
            
    return current

# Validasi saat startup
def validate_settings():
    """Memastikan pengaturan penting tersedia."""
    config = load_config()
    required_keys = [
        "confidence_thresholds.high_gap",
        "min_recommendation_gap",
        "api_settings.delay_seconds"
    ]
    
    for key in required_keys:
        val = get_setting(key)
        if val is None:
            print(f"[Config Error] Pengaturan penting '{key}' hilang dari settings.yaml")
            
validate_settings()