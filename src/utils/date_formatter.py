import pytz
from datetime import datetime
import re

def format_game_display(game_date_et, game_time_et):
    """
    Format display pertandingan:
    - Hari + Tanggal berdasarkan game_date_et (zona waktu ET)
    - Jam + Menit dikonversi ke WIB (Asia/Jakarta)
    """
    et_tz = pytz.timezone('America/New_York')
    wib_tz = pytz.timezone('Asia/Jakarta')
    
    HARI_ID = {
        'Monday': 'Senin', 'Tuesday': 'Selasa',
        'Wednesday': 'Rabu', 'Thursday': 'Kamis',
        'Friday': 'Jumat', 'Saturday': 'Sabtu',
        'Sunday': 'Minggu'
    }
    
    # Bersihkan E(D/S)T label (case-insensitive)
    clean_time = re.sub(r'\s*E[DS]?T\s*$', '', game_time_et, flags=re.IGNORECASE).strip()
    
    # Parse datetime ET
    dt_str = f"{game_date_et} {clean_time}"
    dt_naive = None
    
    # Coba berbagai format parsing
    for fmt in ['%Y-%m-%d %I:%M %p', '%Y-%m-%d %I:%M%p', '%Y-%m-%d %H:%M']:
        try:
            dt_naive = datetime.strptime(dt_str, fmt)
            break
        except:
            continue
            
    if dt_naive is None:
        # Fallback jika gagal parse
        return {
            'display': f"{game_date_et} | {game_time_et}",
            'hari': '',
            'tanggal_et': game_date_et,
            'jam_wib': game_time_et,
            'game_date_et': game_date_et,
            'game_time_wib': game_time_et,
        }
    
    dt_et = et_tz.localize(dt_naive)
    dt_wib = dt_et.astimezone(wib_tz)
    
    # Tanggal dan hari dari ET
    hari_en = dt_et.strftime('%A')
    hari_id = HARI_ID.get(hari_en, hari_en)
    
    # Format tanggal ET (misal: "20 Jun 2026")
    day_num = dt_et.day
    # Peta bulan bahasa indonesia singkat
    BULAN_MAP = {
        'Jan': 'Jan', 'Feb': 'Feb', 'Mar': 'Mar', 'Apr': 'Apr',
        'May': 'Mei', 'Jun': 'Jun', 'Jul': 'Jul', 'Aug': 'Agu',
        'Sep': 'Sep', 'Oct': 'Okt', 'Nov': 'Nov', 'Dec': 'Des'
    }
    month_en = dt_et.strftime('%b')
    month_id = BULAN_MAP.get(month_en, month_en)
    year_num = dt_et.year
    tgl_et = f"{day_num} {month_id} {year_num}"
    
    # Jam dari WIB
    jam_wib = dt_wib.strftime('%H:%M')
    
    return {
        'display': f"{hari_id}, {tgl_et} | {jam_wib} WIB",
        'hari': hari_id,
        'tanggal_et': tgl_et,
        'jam_wib': jam_wib,
        'game_date_et': game_date_et,
        'game_time_wib': jam_wib,
    }
