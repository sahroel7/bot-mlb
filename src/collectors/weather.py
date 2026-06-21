import requests
from datetime import datetime
import math

# Koordinat Lat/Lon untuk semua 30 Stadion MLB
STADIUM_COORDINATES = {
    "Chase Field": {"lat": 33.4455, "lon": -112.0667, "orientation": 0},
    "Truist Park": {"lat": 33.8907, "lon": -84.4678, "orientation": 45},
    "Oriole Park at Camden Yards": {"lat": 39.284, "lon": -76.6215, "orientation": 45},
    "Fenway Park": {"lat": 42.3467, "lon": -71.0972, "orientation": 45},
    "Wrigley Field": {"lat": 41.9484, "lon": -87.6553, "orientation": 22},
    "Guaranteed Rate Field": {"lat": 41.8299, "lon": -87.6339, "orientation": 45},
    "Great American Ball Park": {"lat": 39.0979, "lon": -84.5071, "orientation": 135},
    "Progressive Field": {"lat": 41.4962, "lon": -81.6852, "orientation": 45},
    "Coors Field": {"lat": 39.7559, "lon": -104.9942, "orientation": 45},
    "Comerica Park": {"lat": 42.3392, "lon": -83.0485, "orientation": 45},
    "Minute Maid Park": {"lat": 29.7573, "lon": -95.3555, "orientation": 0},
    "Kauffman Stadium": {"lat": 39.0517, "lon": -94.4803, "orientation": 45},
    "Angel Stadium": {"lat": 33.8003, "lon": -117.8827, "orientation": 45},
    "Dodger Stadium": {"lat": 34.0739, "lon": -118.24, "orientation": 22},
    "loanDepot park": {"lat": 25.7783, "lon": -80.2197, "orientation": 0},
    "American Family Field": {"lat": 43.0284, "lon": -87.9712, "orientation": 0},
    "Target Field": {"lat": 44.9817, "lon": -93.2778, "orientation": 45},
    "Citi Field": {"lat": 40.7571, "lon": -73.8458, "orientation": 45},
    "Yankee Stadium": {"lat": 40.8296, "lon": -73.9262, "orientation": 67},
    "Oakland Coliseum": {"lat": 37.7516, "lon": -122.2005, "orientation": 45},
    "Citizens Bank Park": {"lat": 39.9061, "lon": -75.1665, "orientation": 45},
    "PNC Park": {"lat": 40.4469, "lon": -80.0057, "orientation": 67},
    "Petco Park": {"lat": 32.7073, "lon": -117.1566, "orientation": 22},
    "Oracle Park": {"lat": 37.7786, "lon": -122.3893, "orientation": 67},
    "T-Mobile Park": {"lat": 47.5914, "lon": -122.3323, "orientation": 45},
    "Busch Stadium": {"lat": 38.6226, "lon": -90.1928, "orientation": 135},
    "Tropicana Field": {"lat": 27.7682, "lon": -82.6534, "orientation": 0},
    "Globe Life Field": {"lat": 32.7473, "lon": -97.0811, "orientation": 0},
    "Rogers Centre": {"lat": 43.6414, "lon": -79.3894, "orientation": 0},
    "Nationals Park": {"lat": 38.873, "lon": -77.0074, "orientation": 45}
}

def get_game_weather(venue_name, game_datetime_str):
    """
    Mengambil data cuaca untuk stadion dan waktu pertandingan tertentu.
    
    Args:
        venue_name (str): Nama stadion (harus ada di STADIUM_COORDINATES).
        game_datetime_str (str): Waktu game format ISO (contoh: '2026-06-13T19:10:00Z' atau '2026-06-11 19:10').
        
    Returns:
        dict: Data cuaca (temp, wind, humidity, precipitation).
    """
    # Mencari venue yang cocok (bisa parsial/nama kota untuk robustnes)
    matched_venue = None
    for v_name, details in STADIUM_COORDINATES.items():
        if venue_name.lower() in v_name.lower():
            matched_venue = v_name
            break
            
    if not matched_venue:
        print(f"Venue '{venue_name}' tidak ditemukan dalam database koordinat.")
        return {}

    coord = STADIUM_COORDINATES[matched_venue]
    lat, lon = coord["lat"], coord["lon"]
    
    # Open-Meteo Forecast API
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Konversi game_datetime yang lebih robust
        clean_dt_str = game_datetime_str.split('Z')[0].replace(' ', 'T')
        # Jika panjang string kurang dari detik, tambahkan detik
        if len(clean_dt_str) == 16: # format 'YYYY-MM-DDTHH:MM'
            clean_dt_str += ':00'
            
        game_dt = datetime.strptime(clean_dt_str, '%Y-%m-%dT%H:%M:%S')
        game_hour_str = game_dt.strftime('%Y-%m-%dT%H:00')
        
        # Cari index yang paling mendekati jam pertandingan
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        
        try:
            idx = times.index(game_hour_str)
        except ValueError:
            # Jika tidak pas, ambil index pertama atau handle error
            idx = 0
            
        weather_info = {
            "temperature_fahrenheit": hourly["temperature_2m"][idx],
            "wind_speed_mph": hourly["wind_speed_10m"][idx],
            "wind_direction_degrees": hourly["wind_direction_10m"][idx],
            "humidity_percent": hourly["relative_humidity_2m"][idx],
            "precipitation_probability": hourly["precipitation_probability"][idx],
            "stadium_orientation": coord["orientation"]
        }
        
        return weather_info
        
    except Exception as e:
        print(f"Error get_game_weather: {e}")
        return {}

def interpret_wind_direction(wind_degrees, stadium_orientation):
    """
    Menginterpretasikan arah angin relatif terhadap orientasi stadion.
    
    Angin diukur berdasarkan arah DATANGNYA angin (0=Utara, 90=Timur, dst).
    Stadium orientation adalah arah dari home plate ke center field.
    
    Returns:
        str: "OUTWARD", "INWARD", atau "CROSSWIND".
    """
    # Hitung selisih sudut antara arah tiupan angin (wind + 180) dan orientasi stadion
    wind_blowing_to = (wind_degrees + 180) % 360
    diff = abs(wind_blowing_to - stadium_orientation)
    if diff > 180:
        diff = 360 - diff
        
    # Toleransi sudut (misal 45 derajat)
    if diff <= 45:
        return "OUTWARD" # Angin berhembus ke arah outfield
    elif diff >= 135:
        return "INWARD"  # Angin berhembus ke arah home plate
    else:
        return "CROSSWIND"

if __name__ == "__main__":
    # Test untuk Yankee Stadium
    VENUE = "Yankee Stadium"
    # Gunakan waktu hari ini atau besok untuk testing (Open-Meteo butuh waktu valid)
    GAME_TIME = datetime.now().strftime('%Y-%m-%dT%H:00:00Z')
    
    print(f"--- Testing Weather for {VENUE} at {GAME_TIME} ---")
    weather = get_game_weather(VENUE, GAME_TIME)
    
    if weather:
        print(f"Suhu: {weather['temperature_fahrenheit']}°F")
        print(f"Kelembaban: {weather['humidity_percent']}%")
        print(f"Kecepatan Angin: {weather['wind_speed_mph']} mph")
        
        wind_type = interpret_wind_direction(
            weather['wind_direction_degrees'], 
            weather['stadium_orientation']
        )
        print(f"Tipe Angin: {wind_type} (Arah: {weather['wind_direction_degrees']}°)")
    else:
        print("Gagal mengambil data cuaca.")
