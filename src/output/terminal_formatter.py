"""
Modul untuk memformat output terminal.
Menghasilkan tampilan visual yang indah dan informatif sesuai PRD.
"""

from colorama import Fore, Back, Style, init

# Inisialisasi colorama untuk Windows compatibility
init(autoreset=True)

def format_game_analysis(game_info, analysis):
    """
    Memformat hasil analisis satu pertandingan ke dalam bentuk box drawing.
    
    Args:
        game_info (dict): Data dasar game (tim, venue, waktu).
        analysis (dict): Hasil dari calculate_expected_total_runs.
        
    Returns:
        str: String terformat untuk print.
    """
    # Tentukan Warna Rekomendasi
    rec = analysis.get("recommendation", "SKIP")
    rec_color = Fore.YELLOW
    if "OVER" in rec:
        rec_color = Fore.GREEN
    elif "UNDER" in rec:
        rec_color = Fore.CYAN
        
    # Tentukan Warna Confidence
    conf = analysis.get("confidence", "LOW")
    conf_color = Fore.WHITE
    if "HIGH" in conf:
        conf_color = Fore.RED + Style.BRIGHT
    elif "MEDIUM" in conf:
        conf_color = Fore.YELLOW + Style.BRIGHT

    # Header
    width = 50
    header = f" {game_info['away_team']} @ {game_info['home_team']} | {game_info['game_time'][:10]} "
    border_top = "┏" + "━" * (width-2) + "┓"
    border_mid = "┣" + "━" * (width-2) + "┫"
    border_bot = "┗" + "━" * (width-2) + "┛"

    output = []
    output.append(rec_color + border_top)
    output.append(rec_color + f"┃ {header.center(width-4)} ┃")
    output.append(rec_color + border_mid)
    
    # Data Pasar vs Bot
    output.append(f"┃ 📊 Bullpen.fi O/U Line  : {Fore.CYAN}{game_info.get('polymarket_line', 'N/A')}")
    output.append(f"┃ 🎯 Bot Expected Runs    : {Fore.MAGENTA}{analysis['final_expected_runs']}")
    output.append(f"┃ 📈 Recommendation       : {rec_color}{rec}")
    output.append(f"┃ 🔥 Confidence           : {conf_color}{conf}")
    output.append(f"┃ 📡 Sumber odds          : {Fore.WHITE}{game_info.get('odds_source', 'N/A')}")
    output.append(rec_color + border_mid)
    
    # Key Factors
    output.append(f"┃ {Style.BRIGHT}📋 KEY FACTORS:{Style.RESET_ALL}")

    reasons = analysis.get("reasons", [])

    if not reasons:
        output.append(f"┃  ➖ Semua metrik dalam batas rata-rata")
    else:
        # Filter reasons untuk menampilkan emoji yang relevan
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

            # Wrapping sederhana jika teks terlalu panjang
            clean_reason = reason[:width-6]
            output.append(f"┃  {emoji} {clean_reason}")

    # Tambahan penjelasan untuk rekomendasi SKIP
    if "SKIP" in rec:
        output.append(f"┃")
        output.append(f"┃  ⚖️ Faktor saling menyeimbangkan.")
        output.append(f"┃     Tidak ada edge yang cukup kuat.")

    output.append(rec_color + border_bot)
    
    return "\n".join(output)

def format_daily_summary(all_analyses):
    """
    Memformat ringkasan semua pertandingan dalam bentuk tabel sederhana.
    """
    if not all_analyses:
        return "Tidak ada data analisis untuk hari ini."
        
    header = f"{'GAME':<25} | {'LINE':<6} | {'PROJ':<6} | {'REC':<10} | {'CONF'}"
    separator = "-" * len(header)
    
    rows = [header, separator]
    
    for item in all_analyses:
        game = item['game_info']
        ans = item['analysis']
        
        matchup = f"{game['away_team']} @ {game['home_team']}"
        row = f"{matchup[:25]:<25} | {game.get('polymarket_line', 'N/A'):<6} | {ans['final_expected_runs']:<6} | {ans['recommendation']:<10} | {ans['confidence']}"
        
        if "HIGH" in ans['confidence']:
            rows.append(Fore.RED + Style.BRIGHT + row)
        else:
            rows.append(row)
            
    return "\n".join(rows)

def format_no_data_warning(game_info, missing_data_list):
    """
    Menampilkan peringatan jika data collector gagal mendapatkan data tertentu.
    """
    msg = f"{Fore.YELLOW}[WARNING] {game_info['away_team']} @ {game_info['home_team']}: Data tidak lengkap ({', '.join(missing_data_list)})"
    return msg
