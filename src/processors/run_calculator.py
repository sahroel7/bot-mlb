"""
Modul Inti Kalkulasi Run.
Menyatukan semua modifier untuk menghasilkan prediksi final dan rekomendasi.
"""

from src.processors.pitcher_scorer import calculate_pitcher_score, calculate_fatigue_penalty, calculate_bullpen_risk
from src.processors.offense_scorer import calculate_offense_score, calculate_risp_modifier
from src.processors.environment_scorer import calculate_weather_score, calculate_park_score
from src.processors.streak_detector import detect_offensive_streak, detect_pitcher_form, calculate_momentum_score
from config.config_loader import get_setting

def calculate_base_runs(home_team_stats, away_team_stats):
    """
    Menghitung Base Run Projection berdasarkan rata-rata performa tim.
    Rumus: (Offense Avg + Opponent Defense Avg) / 2
    
    Args:
        home_team_stats (dict): Statistik tim home.
        away_team_stats (dict): Statistik tim away.
        
    Returns:
        float: Proyeksi total run dasar.
    """
    # Jika data runs_allowed tidak tersedia, gunakan baseline liga (sekitar 4.5)
    home_offense = home_team_stats.get('runs_per_game', 4.5)
    away_offense = away_team_stats.get('runs_per_game', 4.5)
    
    # Gunakan ERA tim sebagai proksi untuk runs allowed jika tidak ada data spesifik
    home_defense = home_team_stats.get('team_era', 4.5) 
    away_defense = away_team_stats.get('team_era', 4.5)

    # Proyeksi Run untuk Away Team
    away_proj = (away_offense + home_defense) / 2
    # Proyeksi Run untuk Home Team
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

def calculate_expected_total_runs(game_data):
    """
    Fungsi utama untuk menghitung prediksi total run akhir dengan semua modifier.
    
    Args:
        game_data (dict): Objek besar berisi semua data hasil collect.
        
    Returns:
        dict: Hasil kalkulasi lengkap beserta alasan.
    """
    all_reasons = []
    total_modifier = 0.0
    
    # 1. Base Runs
    base_runs = calculate_base_runs(game_data['home_team_stats'], game_data['away_team_stats'])
    
    # 2. Pitcher Modifiers (Starter & Bullpen)
    hp_mod, hp_reasons = calculate_pitcher_score(game_data['home_pitcher_stats'])
    hf_mod, hf_reasons = calculate_fatigue_penalty(game_data['home_pitcher_last_3'])
    hb_mod, hb_reasons = calculate_bullpen_risk(game_data['home_bullpen_era'])
    
    ap_mod, ap_reasons = calculate_pitcher_score(game_data['away_pitcher_stats'])
    af_mod, af_reasons = calculate_fatigue_penalty(game_data['away_pitcher_last_3'])
    ab_mod, ab_reasons = calculate_bullpen_risk(game_data['away_bullpen_era'])
    
    p_mod = hp_mod + hf_mod + hb_mod + ap_mod + af_mod + ab_mod
    total_modifier += p_mod
    all_reasons.extend(hp_reasons + hf_reasons + hb_reasons + ap_reasons + af_reasons + ab_reasons)
    
    # 3. Offense Modifiers
    ho_mod, ho_reasons = calculate_offense_score(game_data['home_team_stats'], game_data['away_pitcher_stats'])
    ao_mod, ao_reasons = calculate_offense_score(game_data['away_team_stats'], game_data['home_pitcher_stats'])
    
    hr_mod, hr_reasons = calculate_risp_modifier(game_data['home_team_stats'].get('risp_avg'))
    ar_mod, ar_reasons = calculate_risp_modifier(game_data['away_team_stats'].get('risp_avg'))
    
    o_mod = ho_mod + ao_mod + hr_mod + ar_mod
    total_modifier += o_mod
    all_reasons.extend(ho_reasons + ao_reasons + hr_reasons + ar_reasons)

    # 4. Advanced Momentum & Streak (Phase 2 Enhancement)
    home_off_streak = detect_offensive_streak(game_data.get('home_team_last_10', []))
    home_pit_form = detect_pitcher_form(game_data['home_pitcher_stats'], game_data['home_pitcher_last_3'])
    home_momentum_mod = calculate_momentum_score(home_off_streak, home_pit_form)
    
    if home_momentum_mod != 0:
        total_modifier += home_momentum_mod
        all_reasons.append(f"Home Momentum ({home_off_streak['type']} Offense, {home_pit_form['form']} Pitcher): {home_momentum_mod:>+0.2f} run")

    away_off_streak = detect_offensive_streak(game_data.get('away_team_last_10', []))
    away_pit_form = detect_pitcher_form(game_data['away_pitcher_stats'], game_data['away_pitcher_last_3'])
    away_momentum_mod = calculate_momentum_score(away_off_streak, away_pit_form)
    
    if away_momentum_mod != 0:
        total_modifier += away_momentum_mod
        all_reasons.append(f"Away Momentum ({away_off_streak['type']} Offense, {away_pit_form['form']} Pitcher): {away_momentum_mod:>+0.2f} run")
    
    # 5. Environment Modifiers
    w_mod, w_reasons = calculate_weather_score(game_data['weather'])
    park_mod, park_reasons = calculate_park_score(game_data['park_factor'], game_data['home_team_id'])
    
    total_modifier += (w_mod + park_mod)
    all_reasons.extend(w_reasons + park_reasons)
    
    raw_expected_runs = round(base_runs + total_modifier, 2)
    is_coors = game_data.get('home_team_id') == 115
    final_expected_runs, was_clamped = clamp_expected_runs(raw_expected_runs, is_coors)
    
    if was_clamped:
        all_reasons.append("⚠️ Nilai di-normalisasi ke batas realistis MLB")
    
    return {
        "base_runs": base_runs,
        "mod_pitcher": round(p_mod, 2),
        "mod_offense": round(o_mod, 2),
        "mod_env": round(w_mod + park_mod, 2),
        "total_modifier": round(total_modifier, 2),
        "final_expected_runs": final_expected_runs,
        "reasons": all_reasons
    }

def make_recommendation(expected_runs, polymarket_line):
    """
    Menentukan rekomendasi taruhan berdasarkan gap antara prediksi dan market.
    """
    gap = expected_runs - polymarket_line
    min_gap = get_setting("min_recommendation_gap", 0.5)
    
    if gap > min_gap:
        return "OVER ✅"
    elif gap < -min_gap:
        return "UNDER ✅"
    else:
        return "NO BET / SKIP ⚠️"

def calculate_confidence(expected_runs, polymarket_line):
    """
    Menghitung tingkat kepercayaan berdasarkan besarnya gap.
    """
    gap = abs(expected_runs - polymarket_line)
    high_gap = get_setting("confidence_thresholds.high_gap", 1.5)
    med_gap = get_setting("confidence_thresholds.medium_gap", 0.5)
    
    if gap > high_gap:
        return "HIGH 🔥"
    elif gap >= med_gap:
        return "MEDIUM ⚡"
    else:
        return "LOW ⚠️"
