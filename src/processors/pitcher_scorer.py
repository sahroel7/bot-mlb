"""
Modul untuk menghitung skor/bobot kualitas pitcher.
Skor ini akan menjadi modifier terhadap proyeksi run dasar.
"""

def calculate_pitcher_score(pitcher_stats):
    """
    Menghitung skor modifier berdasarkan statistik performa pitcher.
    
    Args:
        pitcher_stats (dict): Data dari get_pitcher_season_stats.
        
    Returns:
        tuple: (score_modifier, reasons)
    """
    score = 0.0
    reasons = []
    
    if not pitcher_stats:
        return 0.0, ["Data pitcher tidak tersedia, menggunakan baseline."]

    # 1. Analisis ERA / FIP (Prioritas FIP)
    # FIP lebih prediktif untuk masa depan dibanding ERA
    base_era = pitcher_stats.get("fip") or pitcher_stats.get("era")
    
    if base_era:
        base_era = float(base_era)
        if base_era > 4.5:
            mod = 0.5
            score += mod
            reasons.append(f"ERA/FIP tinggi ({base_era}): +{mod} run")
        elif base_era < 3.2:
            mod = -0.5
            score += mod
            reasons.append(f"ERA/FIP elit ({base_era}): {mod} run")

    # 2. WHIP (Baserunners)
    whip = pitcher_stats.get("whip")
    if whip:
        whip = float(whip)
        if whip > 1.4:
            mod = 0.3
            score += mod
            reasons.append(f"WHIP tinggi ({whip}): +{mod} run")
        elif whip < 1.1:
            mod = -0.3
            score += mod
            reasons.append(f"WHIP rendah ({whip}): {mod} run")

    # 3. K/9 (Strikeout ability)
    k9 = pitcher_stats.get("k9")
    if k9:
        k9 = float(k9)
        if k9 > 9.5:
            mod = -0.4
            score += mod
            reasons.append(f"K/9 tinggi ({k9}): {mod} run")

    # 4. BB/9 (Control)
    bb9 = pitcher_stats.get("bb9")
    if bb9:
        bb9 = float(bb9)
        if bb9 > 3.5:
            mod = 0.3
            score += mod
            reasons.append(f"Kontrol buruk (BB/9 {bb9}): +{mod} run")

    # 5. HR/9 (Gopher ball risk)
    hr9 = pitcher_stats.get("hr9")
    if hr9:
        hr9 = float(hr9)
        if hr9 > 1.3:
            mod = 0.5
            score += mod
            reasons.append(f"Rawan Home Run (HR/9 {hr9}): +{mod} run")

    # Limitasi score antara -2.0 sampai +2.0
    score = max(min(score, 2.0), -2.0)
    return round(score, 2), reasons

def calculate_fatigue_penalty(last_3_starts):
    """
    Menghitung penalti jika pitcher menunjukkan tanda kelelahan.
    
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
    # Jika > 100 pitch di dua game berurutan -> penalti
    pitch_counts = [s.get("pitch_count") for s in last_3_starts if s.get("pitch_count")]
    
    if len(pitch_counts) >= 2:
        if pitch_counts[0] > 100 and pitch_counts[1] > 100:
            mod = 0.3
            penalty += mod
            reasons.append(f"Beban kerja tinggi (2 start > 100 pitch): +{mod} run")

    # Cek efisiensi (IP per start yang rendah)
    # Jika starter jarang mencapai 6 inning, bullpen akan lebih cepat masuk
    ips = [float(s.get("innings_pitched", 0)) for s in last_3_starts if s.get("innings_pitched")]
    if ips:
        avg_ip = sum(ips) / len(ips)
        if avg_ip < 5.0:
            mod = 0.2
            penalty += mod
            reasons.append(f"Inning pendek (rata-rata {round(avg_ip,1)} IP): +{mod} run (eksposur bullpen)")

    return round(penalty, 2), reasons

def calculate_bullpen_risk(bullpen_era):
    """
    Menghitung risiko run tambahan dari bullpen.
    
    Args:
        bullpen_era (float): ERA bullpen tim.
        
    Returns:
        tuple: (bullpen_modifier, reasons)
    """
    if not bullpen_era:
        return 0.0, []
        
    try:
        bullpen_era = float(bullpen_era)
    except ValueError:
        return 0.0, []
        
    mod = 0.0
    reasons = []
    
    if bullpen_era > 4.5:
        mod = 0.4
        reasons.append(f"Bullpen lemah (ERA {bullpen_era}): +{mod} run")
    elif bullpen_era < 3.5:
        mod = -0.2
        reasons.append(f"Bullpen solid (ERA {bullpen_era}): {mod} run")
        
    return round(mod, 2), reasons
