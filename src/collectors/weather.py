import requests
from datetime import datetime
import math
from src.utils.network import get_request

# Koordinat Lat/Lon untuk semua 30 Stadion MLB beserta Karakteristik Atap/Kubah
STADIUM_COORDINATES = {
    "Chase Field": {"lat": 33.4455, "lon": -112.0667, "orientation": 0, "roof": "retractable"},
    "Truist Park": {"lat": 33.8907, "lon": -84.4678, "orientation": 45, "roof": "open"},
    "Oriole Park at Camden Yards": {"lat": 39.284, "lon": -76.6215, "orientation": 45, "roof": "open"},
    "Fenway Park": {"lat": 42.3467, "lon": -71.0972, "orientation": 45, "roof": "open"},
    "Wrigley Field": {"lat": 41.9484, "lon": -87.6553, "orientation": 22, "roof": "open"},
    "Guaranteed Rate Field": {"lat": 41.8299, "lon": -87.6339, "orientation": 45, "roof": "open"},
    "Great American Ball Park": {"lat": 39.0979, "lon": -84.5071, "orientation": 135, "roof": "open"},
    "Progressive Field": {"lat": 41.4962, "lon": -81.6852, "orientation": 45, "roof": "open"},
    "Coors Field": {"lat": 39.7559, "lon": -104.9942, "orientation": 45, "roof": "open"},
    "Comerica Park": {"lat": 42.3392, "lon": -83.0485, "orientation": 45, "roof": "open"},
    "Minute Maid Park": {"lat": 29.7573, "lon": -95.3555, "orientation": 0, "roof": "retractable"},
    "Kauffman Stadium": {"lat": 39.0517, "lon": -94.4803, "orientation": 45, "roof": "open"},
    "Angel Stadium": {"lat": 33.8003, "lon": -117.8827, "orientation": 45, "roof": "open"},
    "Dodger Stadium": {"lat": 34.0739, "lon": -118.24, "orientation": 22, "roof": "open"},
    "loanDepot park": {"lat": 25.7783, "lon": -80.2197, "orientation": 0, "roof": "retractable"},
    "American Family Field": {"lat": 43.0284, "lon": -87.9712, "orientation": 0, "roof": "retractable"},
    "Target Field": {"lat": 44.9817, "lon": -93.2778, "orientation": 45, "roof": "open"},
    "Citi Field": {"lat": 40.7571, "lon": -73.8458, "orientation": 45, "roof": "open"},
    "Yankee Stadium": {"lat": 40.8296, "lon": -73.9262, "orientation": 67, "roof": "open"},
    "Oakland Coliseum": {"lat": 37.7516, "lon": -122.2005, "orientation": 45, "roof": "open"},
    "Citizens Bank Park": {"lat": 39.9061, "lon": -75.1665, "orientation": 45, "roof": "open"},
    "PNC Park": {"lat": 40.4469, "lon": -80.0057, "orientation": 67, "roof": "open"},
    "Petco Park": {"lat": 32.7073, "lon": -117.1566, "orientation": 22, "roof": "open"},
    "Oracle Park": {"lat": 37.7786, "lon": -122.3893, "orientation": 67, "roof": "open"},
    "T-Mobile Park": {"lat": 47.5914, "lon": -122.3323, "orientation": 45, "roof": "retractable"},
    "Busch Stadium": {"lat": 38.6226, "lon": -90.1928, "orientation": 135, "roof": "open"},
    "Tropicana Field": {"lat": 27.7682, "lon": -82.6534, "orientation": 0, "roof": "dome"},
    "Globe Life Field": {"lat": 32.7473, "lon": -97.0811, "orientation": 0, "roof": "retractable"},
    "Rogers Centre": {"lat": 43.6414, "lon": -79.3894, "orientation": 0, "roof": "retractable"},
    "Nationals Park": {"lat": 38.873, "lon": -77.0074, "orientation": 45, "roof": "open"},
    "Daikin Park": {"lat": 29.7573, "lon": -95.3555, "orientation": 0, "roof": "retractable"},
    "Sutter Health Park": {"lat": 38.5804, "lon": -121.5147, "orientation": 45, "roof": "open"}
}

def get_game_weather(venue_name, game_datetime_str):
    """
    Mengambil data cuaca untuk stadion dan waktu pertandingan tertentu.
    Mengakomodasi penutupan atap untuk stadion kubah/retractable.
    
    Args:
        venue_name (str): Nama stadion (harus ada di STADIUM_COORDINATES).
        game_datetime_str (str): Waktu game format ISO (contoh: '2026-06-13T19:10:00Z' atau '2026-06-11 19:10').
        
    Returns:
        dict: Data cuaca (temp, wind, humidity, precipitation).
    """
    # Mencari venue yang cocok (bisa parsial/nama kota untuk robustnes secara bi-directional)
    matched_venue = None
    for v_name, details in STADIUM_COORDINATES.items():
        if venue_name.lower() in v_name.lower() or v_name.lower() in venue_name.lower():
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
        response = get_request(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Konversi game_datetime yang lebih robust (dari UTC ke lokal menggunakan offset API)
        clean_dt_str = game_datetime_str.split('Z')[0].replace(' ', 'T')
        # Jika panjang string kurang dari detik, tambahkan detik
        if len(clean_dt_str) == 16: # format 'YYYY-MM-DDTHH:MM'
            clean_dt_str += ':00'
            
        game_dt_utc = datetime.strptime(clean_dt_str, '%Y-%m-%dT%H:%M:%S')
        
        # Konversi UTC ke Waktu Lokal menggunakan utc_offset_seconds dari response Open-Meteo
        utc_offset = data.get("utc_offset_seconds", 0)
        from datetime import timedelta
        game_dt_local = game_dt_utc + timedelta(seconds=utc_offset)
        game_hour_str = game_dt_local.strftime('%Y-%m-%dT%H:00')
        
        # Cari index yang paling mendekati jam pertandingan
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        
        try:
            idx = times.index(game_hour_str)
        except ValueError:
            # Jika tidak pas, ambil index pertama atau handle error
            idx = 0
            
        temp_out = hourly["temperature_2m"][idx]
        wind_out = hourly["wind_speed_10m"][idx]
        humidity_out = hourly["relative_humidity_2m"][idx]
        precip_out = hourly["precipitation_probability"][idx]
        
        roof_type = coord.get("roof", "open")
        roof_closed = False
        
        if roof_type == "dome":
            roof_closed = True
        elif roof_type == "retractable":
            # Atap retractable ditutup jika suhu luar ruangan panas (>80°F), dingin (<55°F), atau potensi hujan (>30%)
            if temp_out > 80.0 or temp_out < 55.0 or precip_out > 30.0:
                roof_closed = True
                
        if roof_closed:
            # Menggunakan standar kondisi udara terkontrol di dalam ruangan (Indoor)
            temperature = 72.0
            wind_speed = 0.0
            wind_direction = 0.0
            humidity = 50.0
            precipitation = 0.0
        else:
            temperature = temp_out
            wind_speed = wind_out
            wind_direction = hourly["wind_direction_10m"][idx]
            humidity = humidity_out
            precipitation = precip_out

        weather_info = {
            "temperature_fahrenheit": temperature,
            "wind_speed_mph": wind_speed,
            "wind_direction_degrees": wind_direction,
            "humidity_percent": humidity,
            "precipitation_probability": precipitation,
            "stadium_orientation": coord["orientation"],
            "roof_closed": roof_closed,
            "roof_type": roof_type
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
