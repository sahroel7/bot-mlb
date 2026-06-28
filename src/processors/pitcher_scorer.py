"""
Modul untuk menghitung skor/bobot kualitas pitcher.
Skor ini akan menjadi modifier terhadap proyeksi run dasar.
"""

def calculate_pitcher_score(pitcher_stats):
    """
    Menghitung skor modifier berdasarkan statistik performa pitcher.
    (ERA/FIP sekarang dihitung langsung pada Base Runs untuk menghindari double counting.
     Fungsi ini sekarang fokus pada deviasi metrik sekunder pitcher).
    
    Args:
        pitcher_stats (dict): Data dari get_pitcher_season_stats.
        
    Returns:
        tuple: (score_modifier, reasons)
    """
    score = 0.0
    reasons = []
    
    if not pitcher_stats:
        return 0.0, ["Data pitcher tidak tersedia, menggunakan baseline."]

    # 1. WHIP (Baserunners) - Seimbang
    whip = pitcher_stats.get("whip")
    if whip:
        try:
            whip = float(whip)
            if whip > 1.4:
                mod = 0.3
                score += mod
                reasons.append(f"WHIP tinggi ({whip}): +{mod} run")
            elif whip < 1.1:
                mod = -0.3
                score += mod
                reasons.append(f"WHIP rendah ({whip}): {mod} run")
        except (ValueError, TypeError):
            pass

    # 2. K/9 (Strikeout ability) - Seimbang
    k9 = pitcher_stats.get("k9")
    if k9:
        try:
            k9 = float(k9)
            if k9 > 9.5:
                mod = -0.4
                score += mod
                reasons.append(f"K/9 tinggi ({k9}): {mod} run")
            elif k9 < 6.5:
                mod = 0.3
                score += mod
                reasons.append(f"K/9 rendah ({k9}): +{mod} run")
        except (ValueError, TypeError):
            pass

    # 3. BB/9 (Control) - Seimbang
    bb9 = pitcher_stats.get("bb9")
    if bb9:
        try:
            bb9 = float(bb9)
            if bb9 > 3.5:
                mod = 0.3
                score += mod
                reasons.append(f"Kontrol buruk (BB/9 {bb9}): +{mod} run")
            elif bb9 < 2.0:
                mod = -0.3
                score += mod
                reasons.append(f"Kontrol elit (BB/9 {bb9}): {mod} run")
        except (ValueError, TypeError):
            pass

    # 4. HR/9 (Home Run risk) - Seimbang
    hr9 = pitcher_stats.get("hr9")
    if hr9:
        try:
            hr9 = float(hr9)
            if hr9 > 1.3:
                mod = 0.5
                score += mod
                reasons.append(f"Rawan Home Run (HR/9 {hr9}): +{mod} run")
            elif hr9 < 0.6:
                mod = -0.4
                score += mod
                reasons.append(f"Supresi Home Run elit (HR/9 {hr9}): {mod} run")
        except (ValueError, TypeError):
            pass

    # Limitasi score antara -2.0 sampai +2.0
    score = max(min(score, 2.0), -2.0)
    return round(score, 2), reasons

def calculate_fatigue_penalty(last_3_starts):
    """
    Menghitung penalti kelelahan atau bonus efisiensi berdasarkan start terakhir.
    
    Args:
        last_3_starts (list): Data dari get_pitcher_last_3_starts.
        
    Returns:
        tuple: (fatigue_modifier, reasons)
    """
    penalty = 0.0
    reasons = []
    
    if len(last_3_starts) < 2:
        return 0.0, []

    # Cek Pitch Count 2 start terakhir
    pitch_counts = [s.get("pitch_count") for s in last_3_starts if s.get("pitch_count")]
    
    if len(pitch_counts) >= 2:
        try:
            p1 = int(pitch_counts[0])
            p2 = int(pitch_counts[1])
            if p1 > 100 and p2 > 100:
                mod = 0.3
                penalty += mod
                reasons.append(f"Beban kerja tinggi (2 start > 100 pitch): +{mod} run")
        except (ValueError, TypeError):
            pass

    # Cek efisiensi (IP per start) - Seimbang
    ips = [float(s.get("innings_pitched", 0)) for s in last_3_starts if s.get("innings_pitched")]
    if ips:
        avg_ip = sum(ips) / len(ips)
        if avg_ip < 5.0:
            mod = 0.2
            penalty += mod
            reasons.append(f"Inning pendek (rata-rata {round(avg_ip,1)} IP): +{mod} run (eksposur bullpen)")
        elif avg_ip > 6.2:
            mod = -0.2
            penalty += mod
            reasons.append(f"Inning panjang (rata-rata {round(avg_ip,1)} IP): {mod} run (kurangi eksposur bullpen)")

    return round(penalty, 2), reasons

def calculate_bullpen_risk(bullpen_era):
    """
    Menghitung risiko run dari bullpen tim (Seimbang).
    
    Args:
        bullpen_era (float): ERA bullpen tim.
        
    Returns:
        tuple: (bullpen_modifier, reasons)
    """
    if not bullpen_era:
        return 0.0, []
        
    try:
        bullpen_era = float(bullpen_era)
    except (ValueError, TypeError):
        return 0.0, []
        
    mod = 0.0
    reasons = []
    
    if bullpen_era > 4.5:
        mod = 0.3
        reasons.append(f"Bullpen lemah (ERA {bullpen_era}): +{mod} run")
    elif bullpen_era < 3.3:
        mod = -0.3
        reasons.append(f"Bullpen solid (ERA {bullpen_era}): {mod} run")
        
    return round(mod, 2), reasons
