import sys
import os
from colorama import Fore, Style, init

# Pastikan sys.path mencakup root direktori
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.utils.health_check import run_health_check
from src.scheduler.auto_runner import run_auto_scheduler

init(autoreset=True)

def main():
    print("━" * 60)
    print(f"{Fore.GREEN}{Style.BRIGHT}  🤖 MLB AI Bot — Mode Otomatis  ")
    print("━" * 60)
    print(f"{Fore.YELLOW}Dashboard TIDAK dijalankan. Notifikasi via Telegram/Discord aktif.\n")
    
    # Jalankan health check
    if not run_health_check():
        print(f"\n{Fore.RED}Health check gagal. Menghentikan bot.")
        sys.exit(1)
        
    print(f"\n{Fore.CYAN}Memulai scheduler 24/7...\n")
    run_auto_scheduler()

if __name__ == "__main__":
    main()
