"""
Modul untuk menghitung skor/bobot berdasarkan kondisi lingkungan (cuaca dan stadion).
Skor ini akan menjadi modifier terhadap proyeksi run dasar.
"""

def calculate_weather_score(weather_data):
    """
    Menghitung skor modifier berdasarkan kondisi cuaca.
    
    Args:
        weather_data (dict): Data dari get_game_weather.
        
    Returns:
        tuple: (score_modifier, reasons)
    """
    score = 0.0
    reasons = []
    
    if not weather_data:
        return 0.0, ["Data cuaca tidak tersedia."]

    # 1. Analisis Angin
    wind_speed = weather_data.get("wind_speed_mph", 0)
    wind_dir = weather_data.get("wind_direction_degrees")
    stadium_orient = weather_data.get("stadium_orientation", 0)
    
    # Import interpret logic secara internal untuk menghindari circular import jika ada
    from src.collectors.weather import interpret_wind_direction
    wind_type = interpret_wind_direction(wind_dir, stadium_orient)
    
    if wind_speed > 10:
        if wind_type == "OUTWARD":
            # Angin kencang keluar meningkatkan peluang Home Run
            mod = round(min(0.5 + (wind_speed - 10) * 0.05, 1.2), 2)
            score += mod
            reasons.append(f"Angin OUTWARD kencang ({wind_speed} mph): +{mod} run")
        elif wind_type == "INWARD":
            # Angin kencang ke dalam menahan bola
            mod = round(max(-0.3 - (wind_speed - 10) * 0.04, -0.8), 2)
            score += mod
            reasons.append(f"Angin INWARD kencang ({wind_speed} mph): {mod} run")

    # 2. Suhu Udara (Udara panas = bola lebih terbang)
    temp = weather_data.get("temperature_fahrenheit", 70)
    if temp > 85:
        mod = 0.3
        score += mod
        reasons.append(f"Suhu panas ({temp}°F): +{mod} run (udara tipis)")
    elif temp < 50:
        mod = -0.4
        score += mod
        reasons.append(f"Suhu dingin ({temp}°F): {mod} run (bola kurang elastis)")

    # 3. Kelembaban & Presipitasi
    humidity = weather_data.get("humidity_percent", 50)
    precip_prob = weather_data.get("precipitation_probability", 0)
    if precip_prob > 50 or humidity > 80:
        mod = 0.2
        score += mod
        reasons.append(f"Kelembaban/Hujan ({humidity}% / {precip_prob}%): +{mod} run (grip pitcher terganggu)")

    return round(score, 2), reasons

def calculate_park_score(park_factor, team_id=None):
    """
    Menghitung skor modifier berdasarkan karakteristik stadion (Park Factor).
    
    Args:
        park_factor (int): Nilai park factor dari src/data/park_factors.py.
        team_id (int): ID tim untuk cek kondisi khusus seperti Coors Field.
        
    Returns:
        tuple: (score_modifier, reasons)
    """
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

    # Coors Field Bonus (Team ID 115)
    if team_id == 115:
        mod = 1.0
        score += mod
        reasons.append(f"Coors Field Elevation Bonus: +{mod} run")

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
