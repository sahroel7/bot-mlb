"""
Modul untuk menghitung skor/bobot berdasarkan kondisi lingkungan (cuaca dan stadion).
Skor ini akan menjadi modifier terhadap proyeksi run dasar.
"""

from config.config_loader import get_setting

def calculate_weather_score(weather_data, params_override: dict = None):
    """
    Menghitung skor modifier berdasarkan kondisi cuaca.
    
    Args:
        weather_data (dict): Data dari get_game_weather.
        params_override (dict, optional): Dictionary berisi override parameter.
        
    Returns:
        tuple: (score_modifier, reasons)
    """
    score = 0.0
    reasons = []
    
    if not weather_data:
        return 0.0, ["Data cuaca tidak tersedia."]

    # Cek apakah atap stadion tertutup (kubah/dome/retractable closed)
    if weather_data.get("roof_closed"):
        roof_type = weather_data.get("roof_type", "dome")
        reasons.append(f"Atap stadion DITUTUP ({roof_type}) — Kondisi udara dikontrol: +0.00 run")
        return 0.0, reasons

    # 1. Analisis Angin
    wind_speed = weather_data.get("wind_speed_mph", 0)
    wind_dir = weather_data.get("wind_direction_degrees")
    stadium_orient = weather_data.get("stadium_orientation", 0)
    
    # Import interpret logic secara internal untuk menghindari circular import jika ada
    from src.collectors.weather import interpret_wind_direction
    wind_type = interpret_wind_direction(wind_dir, stadium_orient)
    
    wind_outward_base = get_setting("weather_thresholds.wind_outward_base", 0.3, params_override)
    wind_coefficient_per_mph = get_setting("weather_thresholds.wind_coefficient_per_mph", 0.04, params_override)
    wind_outward_cap = get_setting("weather_thresholds.wind_outward_cap", 0.8, params_override)
    wind_inward_cap = get_setting("weather_thresholds.wind_inward_cap", -0.8, params_override)

    if wind_speed > 10:
        if wind_type == "OUTWARD":
            # Angin kencang keluar meningkatkan peluang Home Run (Seimbang, maks +0.8)
            mod = round(min(wind_outward_base + (wind_speed - 10) * wind_coefficient_per_mph, wind_outward_cap), 2)
            score += mod
            reasons.append(f"Angin OUTWARD kencang ({wind_speed} mph): +{mod} run")
        elif wind_type == "INWARD":
            # Angin kencang ke dalam menahan bola (Seimbang, maks -0.8)
            mod = round(max(-wind_outward_base - (wind_speed - 10) * wind_coefficient_per_mph, wind_inward_cap), 2)
            score += mod
            reasons.append(f"Angin INWARD kencang ({wind_speed} mph): {mod} run")

    # 2. Suhu Udara (Udara panas = bola lebih terbang, udara dingin = bola berat)
    temp = weather_data.get("temperature_fahrenheit", 70)
    if temp > 85:
        mod = 0.3
        score += mod
        reasons.append(f"Suhu panas ({temp}°F): +{mod} run (udara tipis)")
    elif temp < 52:
        mod = -0.3
        score += mod
        reasons.append(f"Suhu dingin ({temp}°F): {mod} run (bola kurang elastis)")

    # 3. Kelembaban & Presipitasi (Memperkecil bias positif)
    humidity = weather_data.get("humidity_percent", 50)
    precip_prob = weather_data.get("precipitation_probability", 0)
    if precip_prob > 50 or humidity > 85:
        mod = 0.1
        score += mod
        reasons.append(f"Kelembaban/Hujan ({humidity}% / {precip_prob}%): +{mod} run (grip pitcher terganggu)")

    return round(score, 2), reasons

def calculate_park_score(park_factor, team_id=None, override_pf=None, params_override: dict = None):
    """
    Menghitung skor modifier berdasarkan karakteristik stadion (Park Factor).
    
    Args:
        park_factor (int): Nilai park factor dari src/data/park_factors.py.
        team_id (int): ID tim untuk cek kondisi khusus seperti Coors Field.
        override_pf (int, optional): Nilai override park factor.
        params_override (dict, optional): Dictionary berisi override parameter.
        
    Returns:
        tuple: (score_modifier, reasons)
    """
    if override_pf is None and params_override is not None:
        override_pf = params_override.get("override_pf")

    if team_id == 115 and override_pf is not None:
        park_factor = override_pf

    score = 0.0
    reasons = []
    
    if park_factor > 105:
        # Hitter's Park
        mod = round((park_factor - 100) * 0.1, 2)
        score += mod
        reasons.append(f"Hitter's Park (PF {park_factor}): +{mod} run")
    elif park_factor < 95:
        # Pitcher's Park
        mod = round((park_factor - 100) * 0.1, 2)
        score += mod
        reasons.append(f"Pitcher's Park (PF {park_factor}): {mod} run")

    # Coors Field Bonus (Team ID 115) - Dinonaktifkan karena double counting dengan Park Factor
    # if team_id == 115:
    #     mod = 1.0
    #     score += mod
    #     reasons.append(f"Coors Field Elevation Bonus: +{mod} run")

    return round(score, 2), reasons

def get_environment_summary(weather_data, park_factor):
    """
    Menghasilkan ringkasan teks kondisi lingkungan.
    """
    if not weather_data:
        return f"Park Factor: {park_factor} (Data cuaca tidak tersedia)"
        
    temp = weather_data.get('temperature_fahrenheit')
    wind = weather_data.get('wind_speed_mph')
    return f"Suhu {temp}°F, Angin {wind} mph, Park Factor {park_factor}"
