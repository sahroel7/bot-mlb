"""
Modul Inti Kalkulasi Run.
Menyatukan semua modifier untuk menghasilkan prediksi final dan rekomendasi.
"""

from src.processors.pitcher_scorer import calculate_pitcher_score, calculate_fatigue_penalty, calculate_bullpen_risk
from src.processors.offense_scorer import calculate_offense_score, calculate_risp_modifier
from src.processors.environment_scorer import calculate_weather_score, calculate_park_score
from src.processors.streak_detector import detect_offensive_streak, detect_pitcher_form, calculate_momentum_score
from config.config_loader import get_setting

def calculate_base_runs(home_team_stats, away_team_stats, home_pitcher_stats=None, away_pitcher_stats=None, home_bullpen_era=None, away_bullpen_era=None, params_override: dict = None):
    """
    Menghitung Base Run Projection berdasarkan rata-rata offense tim dan rata-rata tertimbang pertahanan (Starter + Bullpen).
    Rumus: (Offense Avg + Opponent Weighted Defense ERA) / 2
    
    Args:
        home_team_stats (dict): Statistik tim home.
        away_team_stats (dict): Statistik tim away.
        home_pitcher_stats (dict): Statistik starting pitcher home.
        away_pitcher_stats (dict): Statistik starting pitcher away.
        home_bullpen_era (float/str): ERA bullpen tim home.
        away_bullpen_era (float/str): ERA bullpen tim away.
        params_override (dict, optional): Dictionary berisi override parameter.
        
    Returns:
        float: Proyeksi total run dasar.
    """
    # Rata-rata runs per game offense
    home_offense = home_team_stats.get('runs_per_game', 4.5)
    away_offense = away_team_stats.get('runs_per_game', 4.5)
    
    try:
        home_offense = float(home_offense)
    except (ValueError, TypeError):
        home_offense = 4.5
        
    try:
        away_offense = float(away_offense)
    except (ValueError, TypeError):
        away_offense = 4.5
    
    def get_stabilized_pitcher_val(pitcher_stats, team_fallback_era):
        if not pitcher_stats:
            return team_fallback_era
        val = pitcher_stats.get('fip') or pitcher_stats.get('era')
        if not val or val == '.---':
            return team_fallback_era
        try:
            val = float(val)
        except:
            return team_fallback_era
        
        # Parse innings pitched
        ip_str = pitcher_stats.get('innings_pitched', '0')
        try:
            if '.' in str(ip_str):
                parts = str(ip_str).split('.')
                ip = float(parts[0]) + (float(parts[1]) / 3.0)
            else:
                ip = float(ip_str)
        except:
            ip = 0.0
            
        # Blending logic: jika IP < threshold, stabilkan ke team_fallback_era
        ip_stabilization_threshold = get_setting('pitcher_thresholds.ip_stabilization_threshold', 40.0, params_override)
        if ip < ip_stabilization_threshold:
            weight = ip / ip_stabilization_threshold if ip_stabilization_threshold > 0.0 else 1.0
            return round((val * weight) + (team_fallback_era * (1.0 - weight)), 2)
        return val

    def get_weighted_defense_val(pitcher_stats, team_fallback_era, bullpen_era):
        blended_starter = get_stabilized_pitcher_val(pitcher_stats, team_fallback_era)
        if not pitcher_stats:
            return blended_starter
            
        # Rata-rata IP per start
        ip_per_start = pitcher_stats.get('ip_per_start')
        try:
            ip_per_start = float(ip_per_start) if ip_per_start is not None else 5.0
        except:
            ip_per_start = 5.0
            
        # Clamp IP per start ke batas realistis starting pitcher (4.0 - 7.0 inning)
        if ip_per_start <= 0.0:
            ip_per_start = 5.0
        elif ip_per_start < 4.0:
            ip_per_start = 4.0
        elif ip_per_start > 7.0:
            ip_per_start = 7.0
            
        # Ambil ERA bullpen
        try:
            b_era = float(bullpen_era) if bullpen_era is not None else team_fallback_era
        except:
            b_era = team_fallback_era
            
        # Hitung weighted defense: (Starter ERA * IP/9) + (Bullpen ERA * (9-IP)/9)
        weighted_val = (blended_starter * (ip_per_start / 9.0)) + (b_era * ((9.0 - ip_per_start) / 9.0))
        return round(weighted_val, 2)

    try:
        home_team_era = float(home_team_stats.get('team_era', 4.5))
    except:
        home_team_era = 4.5
        
    try:
        away_team_era = float(away_team_stats.get('team_era', 4.5))
    except:
        away_team_era = 4.5

    home_defense_val = get_weighted_defense_val(home_pitcher_stats, home_team_era, home_bullpen_era)
    away_defense_val = get_weighted_defense_val(away_pitcher_stats, away_team_era, away_bullpen_era)

    # Proyeksi Run untuk Away Team (Away Offense vs Home Defense)
    away_proj = (away_offense + home_defense_val) / 2
    # Proyeksi Run untuk Home Team (Home Offense vs Away Defense)
    home_proj = (home_offense + away_defense_val) / 2
    
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
    Fungsi utama untuk menghitung prediksi total run akhir dengan semua modifier.
    
    Args:
        game_data (dict): Objek besar berisi semua data hasil collect.
        params_override (dict, optional): Dictionary berisi override parameter.
        
    Returns:
        dict: Hasil kalkulasi lengkap beserta alasan.
    """
    all_reasons = []
    total_modifier = 0.0

    # Hapus modifikasi manual +15% di Coors Field untuk menghindari double counting dengan Park Factor
    # (Coors Field sudah diakomodasi oleh Park Factor +1.3 run)
    home_pitcher_stats = game_data.get('home_pitcher_stats', {}).copy() if game_data.get('home_pitcher_stats') else {}
    away_pitcher_stats = game_data.get('away_pitcher_stats', {}).copy() if game_data.get('away_pitcher_stats') else {}
    
    # 1. Base Runs (Menggunakan starter + bullpen stats secara langsung untuk akurasi)
    base_runs = calculate_base_runs(
        game_data['home_team_stats'], 
        game_data['away_team_stats'],
        home_pitcher_stats,
        away_pitcher_stats,
        game_data.get('home_bullpen_era'),
        game_data.get('away_bullpen_era'),
        params_override=params_override
    )
    
    # 2. Pitcher Modifiers (Starter & Bullpen)
    hp_mod, hp_reasons = calculate_pitcher_score(home_pitcher_stats, params_override=params_override)
    hf_mod, hf_reasons = calculate_fatigue_penalty(game_data['home_pitcher_last_3'], params_override=params_override)
    hb_mod, hb_reasons = calculate_bullpen_risk(game_data['home_bullpen_era'])
    
    ap_mod, ap_reasons = calculate_pitcher_score(away_pitcher_stats, params_override=params_override)
    af_mod, af_reasons = calculate_fatigue_penalty(game_data['away_pitcher_last_3'], params_override=params_override)
    ab_mod, ab_reasons = calculate_bullpen_risk(game_data['away_bullpen_era'])
    
    # hb_mod/ab_mod sengaja tidak ditambahkan -- bullpen ERA sudah terhitung di base_runs (weighted defense), lihat get_weighted_defense_val().
    p_mod = hp_mod + hf_mod + ap_mod + af_mod
    total_modifier += p_mod
    all_reasons.extend(hp_reasons + hf_reasons + ap_reasons + af_reasons)

    if hb_reasons:
        all_reasons.append("[Info] Bullpen Home tercermin di base_runs (weighted defense), bukan modifier tambahan.")
    if ab_reasons:
        all_reasons.append("[Info] Bullpen Away tercermin di base_runs (weighted defense), bukan modifier tambahan.")
    
    enable_bullpen_fatigue = get_setting("enable_bullpen_fatigue", False, params_override)
    if enable_bullpen_fatigue:
        from src.processors.bullpen_workload_scorer import calculate_bullpen_fatigue_score
        hbf_mod, hbf_reasons = calculate_bullpen_fatigue_score(game_data.get('home_bullpen_workload_3d'))
        abf_mod, abf_reasons = calculate_bullpen_fatigue_score(game_data.get('away_bullpen_workload_3d'))
        total_modifier += (hbf_mod + abf_mod)
        all_reasons.extend(hbf_reasons + abf_reasons)
    
    # 3. Offense Modifiers
    ho_mod, ho_reasons = calculate_offense_score(game_data['home_team_stats'], away_pitcher_stats)
    ao_mod, ao_reasons = calculate_offense_score(game_data['away_team_stats'], home_pitcher_stats)
    
    hr_mod, hr_reasons = calculate_risp_modifier(game_data['home_team_stats'].get('risp_avg'))
    ar_mod, ar_reasons = calculate_risp_modifier(game_data['away_team_stats'].get('risp_avg'))
    
    o_mod = ho_mod + ao_mod + hr_mod + ar_mod
    total_modifier += o_mod
    all_reasons.extend(ho_reasons + ao_reasons + hr_reasons + ar_reasons)
    
    # 3.1 Lineup Strength Modifiers (Fase 2 Peningkatan - Lineup Aktif)
    game_id = game_data.get('game_id')
    if game_id:
        from src.collectors.team_offense import analyze_lineup_strength
        # Home team lineup
        home_lineup_analysis = analyze_lineup_strength(game_id, game_data.get('home_team_id'), game_data.get('home_last_10_raw', []))
        if home_lineup_analysis.get('active'):
            home_absents = home_lineup_analysis.get('absent_players', [])
            if home_absents:
                total_modifier += home_lineup_analysis['modifier']
                all_reasons.append(f"[Lineup] Hitter kunci Home absen ({', '.join(home_absents)}): {home_lineup_analysis['modifier']:>+0.2f} run")
                
        # Away team lineup
        away_lineup_analysis = analyze_lineup_strength(game_id, game_data.get('away_team_id'), game_data.get('away_last_10_raw', []))
        if away_lineup_analysis.get('active'):
            away_absents = away_lineup_analysis.get('absent_players', [])
            if away_absents:
                total_modifier += away_lineup_analysis['modifier']
                all_reasons.append(f"[Lineup] Hitter kunci Away absen ({', '.join(away_absents)}): {away_lineup_analysis['modifier']:>+0.2f} run")

    # 4. Advanced Momentum & Streak (Phase 2 Enhancement)
    home_off_streak = detect_offensive_streak(game_data.get('home_team_last_10', []))
    home_pit_form = detect_pitcher_form(home_pitcher_stats, game_data['home_pitcher_last_3'])
    home_momentum_mod = calculate_momentum_score(home_off_streak, home_pit_form)
    
    if home_momentum_mod != 0:
        total_modifier += home_momentum_mod
        all_reasons.append(f"Home Momentum ({home_off_streak['type']} Offense, {home_pit_form['form']} Pitcher): {home_momentum_mod:>+0.2f} run")

    away_off_streak = detect_offensive_streak(game_data.get('away_team_last_10', []))
    away_pit_form = detect_pitcher_form(away_pitcher_stats, game_data['away_pitcher_last_3'])
    away_momentum_mod = calculate_momentum_score(away_off_streak, away_pit_form)
    
    if away_momentum_mod != 0:
        total_modifier += away_momentum_mod
        all_reasons.append(f"Away Momentum ({away_off_streak['type']} Offense, {away_pit_form['form']} Pitcher): {away_momentum_mod:>+0.2f} run")
    
    # 5. Environment Modifiers
    w_mod, w_reasons = calculate_weather_score(game_data['weather'], params_override=params_override)
    park_mod, park_reasons = calculate_park_score(game_data['park_factor'], game_data['home_team_id'], params_override=params_override)
    
    total_modifier += (w_mod + park_mod)
    all_reasons.extend(w_reasons + park_reasons)
    
    raw_expected_runs = round(base_runs + total_modifier, 2)
    is_coors = game_data.get('home_team_id') == 115
    final_expected_runs, was_clamped = clamp_expected_runs(raw_expected_runs, is_coors)
    
    if was_clamped:
        all_reasons.append("⚠️ Nilai di-normalisasi ke batas realistis MLB")
    
    volatility_score = 0
    if abs(w_mod) >= 0.6:  # cuaca ekstrem
        volatility_score += 1
    if park_mod >= 1.5 or park_mod <= -1.0:  # park factor ekstrem
        volatility_score += 1
    if not home_pitcher_stats or not away_pitcher_stats:
        volatility_score += 1

    # Inning pendek pemicu volatility_score jika ada di hf_reasons atau af_reasons
    if any("Inning pendek" in r for r in hf_reasons) or any("Inning pendek" in r for r in af_reasons):
        volatility_score += 1

    return {
        "base_runs": base_runs,
        "mod_pitcher": round(p_mod, 2),
        "mod_offense": round(o_mod, 2),
        "mod_env": round(w_mod + park_mod, 2),
        "total_modifier": round(total_modifier, 2),
        "final_expected_runs": final_expected_runs,
        "reasons": all_reasons,
        "volatility_score": volatility_score
    }

def make_recommendation(expected_runs, polymarket_line, params_override: dict = None, volatility_score=0):
    """
    Menentukan rekomendasi taruhan berdasarkan gap antara prediksi dan market.
    """
    gap = expected_runs - polymarket_line
    enable_dynamic_gap = get_setting("enable_dynamic_gap", False, params_override)
    min_gap = get_setting("min_recommendation_gap", 0.5, params_override)
    
    if enable_dynamic_gap and volatility_score > 0:
        # Setiap 1 poin volatilitas menambah 0.25 run ke syarat gap minimum
        min_gap = min_gap + (volatility_score * 0.25)
        
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
