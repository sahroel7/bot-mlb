import sys
import os
import subprocess
import webbrowser
import time
from colorama import Fore, Style, init

init(autoreset=True)

def check_streamlit():
    """Memeriksa apakah streamlit terinstal di environment saat ini."""
    try:
        import streamlit
        return True
    except ImportError:
        return False

def main():
    print("━" * 60)
    print(f"{Fore.MAGENTA}{Style.BRIGHT}  📊 MLB AI Bot — Mode Dashboard  ")
    print("━" * 60)
    
    print(f"{Fore.YELLOW}⚠️  Dashboard ini hanya untuk review manual.")
    print(f"{Fore.YELLOW}⚠️  Tutup dashboard ini setelah selesai review agar laptop tidak berat.")
    print(f"{Fore.YELLOW}⚠️  Bot scheduler tetap berjalan terpisah di terminal lain.\n")
    
    if not check_streamlit():
        print(f"{Fore.RED}Error: Streamlit belum terinstall.")
        print(f"{Fore.WHITE}Jalankan perintah berikut untuk menginstall dependensi dashboard:")
        print(f"{Fore.CYAN}pip install -r requirements-dashboard.txt\n")
        sys.exit(1)
        
    print(f"{Fore.GREEN}Menjalankan Streamlit Server...")
    
    # Buka browser otomatis ke localhost:8501
    # Diberi jeda sedikit agar server sempat menyala sebelum browser terbuka
    try:
        # Menjalankan Streamlit sebagai subprocess
        # Kita gunakan python -m streamlit agar menggunakan eksekutor python yang sama
        cmd = [sys.executable, "-m", "streamlit", "run", "dashboard/app.py"]
        
        # Buka browser di background
        print(f"{Fore.WHITE}Membuka browser di http://localhost:8501 ...")
        
        # Eksekusi server
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}Dashboard berhasil ditutup. Sampai jumpa!")
    except Exception as e:
        print(f"\n{Fore.RED}Terjadi kesalahan saat menjalankan dashboard: {e}")

if __name__ == "__main__":
    main()
