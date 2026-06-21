"""
Modul untuk menghitung skor/bobot kualitas offense (penyerangan).
Skor ini akan menjadi modifier terhadap proyeksi run dasar.
"""

def calculate_offense_score(team_offense_stats, opposing_pitcher_stats):
    """
    Menghitung skor modifier berdasarkan statistik performa offense tim.
    
    Args:
        team_offense_stats (dict): Data dari get_team_season_offense.
        opposing_pitcher_stats (dict): Data dari get_pitcher_season_stats (milik lawan).
        
    Returns:
        tuple: (score_modifier, reasons)
    """
    score = 0.0
    reasons = []
    
    if not team_offense_stats:
        return 0.0, ["Data offense tidak tersedia."]

    # 1. OPS (On-base + Slugging)
    ops = team_offense_stats.get("ops")
    if ops:
        ops = float(ops)
        if ops > 0.800:
            mod = 0.3
            score += mod
            reasons.append(f"Offense berbahaya (OPS {ops}): +{mod} run")
        elif ops < 0.700:
            mod = -0.3
            score += mod
            reasons.append(f"Offense lemah (OPS {ops}): {mod} run")

    # 2. Matchup K% vs K/9
    # Jika tim sering strikeout (K% tinggi) dan pitcher lawan jago strikeout (K/9 tinggi)
    team_k_pct = team_offense_stats.get("k_pct")
    pitcher_k9 = opposing_pitcher_stats.get("k9")
    
    if team_k_pct and pitcher_k9:
        if float(team_k_pct) > 22.0 and float(pitcher_k9) > 9.0:
            mod = -0.4
            score += mod
            reasons.append(f"Matchup buruk: Tim K% tinggi ({team_k_pct}) vs Pitcher K/9 tinggi ({pitcher_k9}): {mod} run")

    # 3. BB% (Disiplin/Sabar)
    bb_pct = team_offense_stats.get("bb_pct")
    if bb_pct:
        if float(bb_pct) > 10.0:
            mod = 0.2
            score += mod
            reasons.append(f"Disiplin tinggi (BB% {bb_pct}): +{mod} run (eksposur baserunner)")

    # Limitasi score antara -1.0 sampai +1.0
    score = max(min(score, 1.0), -1.0)
    return round(score, 2), reasons

def calculate_platoon_advantage(lineup, pitcher_handedness):
    """
    Menghitung keuntungan platoon (Matchup Kiri/Kanan).
    Lineup berisi list pemain (untuk MVP kita asumsikan data handedness bisa didapat nanti 
    atau gunakan perkiraan porsi lineup).
    
    Args:
        lineup (list): List pemain.
        pitcher_handedness (str): "L" atau "R".
        
    Returns:
        tuple: (modifier, reasons)
    """
    # Sebagai MVP, kita gunakan simulasi porsi lineup jika data handedness pemain individual belum lengkap.
    # Secara umum, lineup yang memiliki porsi berlawanan dengan pitcher diuntungkan.
    return 0.0, [] # Placeholder untuk Phase 2 Enhanced

def calculate_streak_modifier(streak_status):
    """
    Memberikan bonus/penalti berdasarkan kondisi streak terakhir.
    
    Args:
        streak_status (str): "HOT", "COLD", atau "NEUTRAL".
        
    Returns:
        tuple: (modifier, reasons)
    """
    if streak_status == "HOT":
        return 0.5, ["Tim sedang dalam kondisi HOT: +0.5 run"]
    elif streak_status == "COLD":
        return -0.5, ["Tim sedang dalam kondisi COLD: -0.5 run"]
    return 0.0, []

def calculate_risp_modifier(risp_avg):
    """
    Menghitung modifier berdasarkan performa dengan Runner in Scoring Position.
    
    Args:
        risp_avg (str/float): Batting average saat RISP.
        
    Returns:
        tuple: (modifier, reasons)
    """
    if not risp_avg or risp_avg == ".---":
        return 0.0, []
        
    avg = float(risp_avg)
    if avg > 0.280:
        mod = 0.2
        return mod, [f"Efisien RISP ({avg}): +{mod} run"]
    elif avg < 0.220:
        mod = -0.2
        return mod, [f"Buruk RISP ({avg}): {mod} run"]
        
    return 0.0, []
