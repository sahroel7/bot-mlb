"""
Modul Inti Kalkulasi Run (Kalibrasi Multiplikatif).
Menyatukan semua modifier untuk menghasilkan prediksi final dan rekomendasi.
"""

from config.config_loader import get_setting

def calculate_base_runs(home_team_stats, away_team_stats, home_pitcher_stats=None, away_pitcher_stats=None, home_bullpen_era=None, away_bullpen_era=None, params_override: dict = None):
    """
    Menghitung Base Run Projection berdasarkan rata-rata offense tim dan defense starter pitcher.
    Rumus: (Offense Avg + Opponent Blended Defense ERA) / 2
    """
    # Rata-rata runs per game offense
    home_offense = home_team_stats.get('runs_per_game', 4.5)
    away_offense = away_team_stats.get('runs_per_game', 4.5)
    
    try: home_offense = float(home_offense)
    except: home_offense = 4.5
    try: away_offense = float(away_offense)
    except: away_offense = 4.5
    
    # Team ERA fallbacks
    try: home_team_era = float(home_team_stats.get('team_era', 4.5))
    except: home_team_era = 4.5
    try: away_team_era = float(away_team_stats.get('team_era', 4.5))
    except: away_team_era = 4.5
    
    # Get blended defense values
    def get_blended_defense(pitcher_stats, team_era, bullpen_era):
        starter_era = pitcher_stats.get('fip') or pitcher_stats.get('era') if pitcher_stats else None
        try:
            starter_era = float(starter_era) if starter_era is not None and starter_era != '.---' else team_era
        except:
            starter_era = team_era
            
        # Stabilize starter if IP is low (e.g. < 40 IP)
        try:
            ip_str = pitcher_stats.get('innings_pitched', '0')
            if '.' in str(ip_str):
                parts = str(ip_str).split('.')
                ip = float(parts[0]) + (float(parts[1]) / 3.0)
            else:
                ip = float(ip_str)
        except:
            ip = 0.0
            
        ip_stabilization_threshold = get_setting('pitcher_thresholds.ip_stabilization_threshold', 40.0, params_override)
        if ip < ip_stabilization_threshold:
            weight = ip / ip_stabilization_threshold
            starter_era = (starter_era * weight) + (team_era * (1.0 - weight))
            
        # Get bullpen ERA
        try: b_era = float(bullpen_era) if bullpen_era is not None else team_era
        except: b_era = team_era
        
        # Blending berdasarkan IP per start
        try: ip_per_start = float(pitcher_stats.get('ip_per_start')) if pitcher_stats and pitcher_stats.get('ip_per_start') else 5.0
        except: ip_per_start = 5.0
        
        ip_per_start = max(min(ip_per_start, 7.0), 4.0)
        
        weighted_val = (starter_era * (ip_per_start / 9.0)) + (b_era * ((9.0 - ip_per_start) / 9.0))
        return weighted_val

    home_defense = get_blended_defense(home_pitcher_stats, home_team_era, home_bullpen_era)
    away_defense = get_blended_defense(away_pitcher_stats, away_team_era, away_bullpen_era)
    
    away_proj = (away_offense + home_defense) / 2
    home_proj = (home_offense + away_defense) / 2
    return round(away_proj + home_proj, 2)

def clamp_expected_runs(raw_value, is_coors_field):
    """
    Membatasi nilai proyeksi run agar tetap realistis dalam konteks MLB.
    """
    max_val = 17.0 if is_coors_field else 15.0
    min_val = 4.0
    
    clamped_value = max(min(raw_value, max_val), min_val)
    was_clamped = clamped_value != raw_value
    
    return clamped_value, was_clamped

def calculate_expected_total_runs(game_data, params_override: dict = None):
    """
    Fungsi utama untuk menghitung prediksi total run akhir dengan pengali multiplikatif.
    """
    all_reasons = []
    
    home_pitcher_stats = game_data.get('home_pitcher_stats', {}).copy() if game_data.get('home_pitcher_stats') else {}
    away_pitcher_stats = game_data.get('away_pitcher_stats', {}).copy() if game_data.get('away_pitcher_stats') else {}
    
    # 1. Base Runs (Starter & Bullpen blend)
    base_runs = calculate_base_runs(
        game_data['home_team_stats'], 
        game_data['away_team_stats'],
        home_pitcher_stats,
        away_pitcher_stats,
        game_data.get('home_bullpen_era'),
        game_data.get('away_bullpen_era'),
        params_override=params_override
    )
    
    # 2. Multiplicative Modifiers
    mult_env = 1.0
    mult_offense = 1.0
    mult_pitcher = 1.0
    
    # 2.1 Park Factor
    pf = game_data.get('park_factor', 100)
    try:
        pf = float(pf)
        # Park factor effect: e.g. PF 113 -> * 1.091. PF 91 -> * 0.937.
        pf_effect = (pf - 100.0) * 0.007
        mult_env *= (1.0 + pf_effect)
        if pf != 100.0:
            all_reasons.append(f"[Park Factor] Stadion PF {pf}: x{1.0 + pf_effect:.2f}")
    except:
        pass
        
    # 2.2 Weather
    weather = game_data.get('weather', {})
    temp = weather.get('temp_f')
    wind_speed = weather.get('wind_speed_mph')
    wind_dir = weather.get('wind_dir')
    
    if temp:
        try:
            t = float(temp)
            if t > 85:
                mult_env *= 1.03
                all_reasons.append(f"[Cuaca] Suhu panas ({t}°F): x1.03")
            elif t < 50:
                mult_env *= 0.97
                all_reasons.append(f"[Cuaca] Suhu dingin ({t}°F): x0.97")
        except:
            pass
            
    if wind_speed and wind_dir:
        try:
            w = float(wind_speed)
            if "out" in str(wind_dir).lower() or "LF" in str(wind_dir) or "RF" in str(wind_dir) or "CF" in str(wind_dir):
                if w > 10:
                    wind_effect = min(w - 10, 15) * 0.002
                    mult_env *= (1.0 + wind_effect)
                    all_reasons.append(f"[Cuaca] Angin OUTWARD ({w} mph): x{1.0 + wind_effect:.2f}")
            elif "in" in str(wind_dir).lower():
                if w > 10:
                    wind_effect = min(w - 10, 15) * 0.002
                    mult_env *= (1.0 - wind_effect)
                    all_reasons.append(f"[Cuaca] Angin INWARD ({w} mph): x{1.0 - wind_effect:.2f}")
        except:
            pass
            
    # 2.3 Offense OPS
    home_ops = game_data.get('home_team_stats', {}).get('ops')
    away_ops = game_data.get('away_team_stats', {}).get('ops')
    try:
        if home_ops and float(home_ops) > 0.800:
            mult_offense *= 1.02
            all_reasons.append(f"[Offense] Home OPS tinggi ({home_ops}): x1.02")
        elif home_ops and float(home_ops) < 0.700:
            mult_offense *= 0.98
            all_reasons.append(f"[Offense] Home OPS rendah ({home_ops}): x0.98")
    except:
        pass
    try:
        if away_ops and float(away_ops) > 0.800:
            mult_offense *= 1.02
            all_reasons.append(f"[Offense] Away OPS tinggi ({away_ops}): x1.02")
        elif away_ops and float(away_ops) < 0.700:
            mult_offense *= 0.98
            all_reasons.append(f"[Offense] Away OPS rendah ({away_ops}): x0.98")
    except:
        pass

    # 2.4 Momentum / Streak
    home_streak = game_data.get('home_streak')
    away_streak = game_data.get('away_streak')
    if home_streak == 'HOT':
        mult_offense *= 1.01
        all_reasons.append("[Momentum] Home Streak HOT: x1.01")
    elif home_streak == 'COLD':
        mult_offense *= 0.99
        all_reasons.append("[Momentum] Home Streak COLD: x0.99")
        
    if away_streak == 'HOT':
        mult_offense *= 1.01
        all_reasons.append("[Momentum] Away Streak HOT: x1.01")
    elif away_streak == 'COLD':
        mult_offense *= 0.99
        all_reasons.append("[Momentum] Away Streak COLD: x0.99")
        
    # 2.5 Pitcher Fatigue (avg IP per start in last 3 starts)
    def get_fatigue_penalty_multiplier(last_3, side_name):
        if not last_3 or len(last_3) < 2:
            return 1.0, None
        try:
            ips = [float(s.get('innings_pitched', 5.0)) for s in last_3]
            avg_ip = sum(ips) / len(ips)
            if avg_ip < 5.0:
                return 1.02, f"[Fatigue] {side_name} starter avg IP pendek ({avg_ip:.1f} IP): x1.02"
            elif avg_ip > 6.2:
                return 0.98, f"[Fatigue] {side_name} starter avg IP panjang ({avg_ip:.1f} IP): x0.98"
        except:
            pass
        return 1.0, None
        
    h_f_mult, h_f_msg = get_fatigue_penalty_multiplier(game_data.get('home_pitcher_last_3'), "Home")
    if h_f_msg:
        mult_pitcher *= h_f_mult
        all_reasons.append(h_f_msg)
        
    a_f_mult, a_f_msg = get_fatigue_penalty_multiplier(game_data.get('away_pitcher_last_3'), "Away")
    if a_f_msg:
        mult_pitcher *= a_f_mult
        all_reasons.append(a_f_msg)
        
    # Combined Multiplier
    multiplier = mult_env * mult_offense * mult_pitcher
    raw_expected_runs = round(base_runs * multiplier, 2)
    is_coors = game_data.get('home_team_id') == 115
    final_expected_runs, was_clamped = clamp_expected_runs(raw_expected_runs, is_coors)
    
    if was_clamped:
        all_reasons.append("⚠️ Nilai di-normalisasi ke batas realistis MLB")
        
    return {
        "base_runs": base_runs,
        "mod_pitcher": round(mult_pitcher - 1.0, 2),
        "mod_offense": round(mult_offense - 1.0, 2),
        "mod_env": round(mult_env - 1.0, 2),
        "total_modifier": round(multiplier - 1.0, 2),
        "final_expected_runs": final_expected_runs,
        "reasons": all_reasons
    }

def make_recommendation(expected_runs, polymarket_line, params_override: dict = None):
    """
    Menentukan rekomendasi taruhan berdasarkan gap antara prediksi dan market.
    """
    gap = expected_runs - polymarket_line
    min_gap = get_setting("min_recommendation_gap", 0.5, params_override)
    
    if gap >= min_gap:
        return "OVER ✅"
    elif gap <= -min_gap:
        return "UNDER ✅"
    else:
        return "NO BET / SKIP ⚠️"

def calculate_confidence(expected_runs, polymarket_line, params_override: dict = None):
    """
    Menghitung tingkat kepercayaan berdasarkan besarnya gap.
    """
    gap = abs(expected_runs - polymarket_line)
    high_gap = get_setting("confidence_thresholds.high_gap", 1.5, params_override)
    med_gap = get_setting("confidence_thresholds.medium_gap", 0.5, params_override)
    
    if gap > high_gap:
        return "HIGH 🔥"
    elif gap >= med_gap:
        return "MEDIUM ⚡"
    else:
        return "LOW ⚠️"
