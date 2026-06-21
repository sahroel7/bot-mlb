"""
Modul Sistem Logging.
Bertugas mencatat semua aktivitas bot ke terminal dan file rotasi harian.
Membaca level log dari file .env.
"""

import logging
from logging.handlers import TimedRotatingFileHandler
import os
from dotenv import load_dotenv

load_dotenv()

# Direktori khusus untuk file log
LOG_DIR = "logs"

def setup_logger(name="MLB_Bot"):
    """
    Membuat dan mengonfigurasi logger terpusat.
    
    Args:
        name (str): Nama logger (default: MLB_Bot).
        
    Returns:
        logging.Logger: Objek logger yang siap digunakan.
    """
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        
    # Ambil level log dari environment (Default: INFO)
    env_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    level_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    log_level = level_mapping.get(env_log_level, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Cegah duplikasi handler jika fungsi dipanggil berkali-kali
    if logger.handlers:
        return logger

    # Format log standar: [TIMESTAMP] [LEVEL] [MODULE] Pesan
    # %(name)s bisa merepresentasikan modul
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # 1. Handler untuk Console (Terminal)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Handler untuk File (Rotating harian)
    # File akan di-rotate setiap 'midnight' dan disimpan maksimal 7 hari (backupCount=7)
    log_file_path = os.path.join(LOG_DIR, "bot.log")
    file_handler = TimedRotatingFileHandler(
        log_file_path, 
        when="midnight", 
        interval=1, 
        backupCount=7, 
        encoding='utf-8'
    )
    # Ubah format penamaan rotasi agar menjadi bot_YYYY-MM-DD.log
    file_handler.suffix = "%Y-%m-%d"
    
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Instansiasi global logger agar bisa langsung diimport oleh modul lain
logger = setup_logger()