"""
File Konfigurasi Eksperimen Shadow Testing.
Menyimpan versi baseline produksi dan versi eksperimental yang sedang diuji.

ATURAN EKSPERIMEN:
- Menambahkan entri baru ke EXPERIMENT_VERSIONS berarti membuat satu eksperimen baru.
- JANGAN menggabungkan lebih dari satu parameter berbeda dalam satu versi eksperimen
  (misal: jangan mengubah min_recommendation_gap dan ip_stabilization_threshold sekaligus dalam satu versi)
  agar kita bisa mengukur dampak masing-masing parameter secara terisolasi.
"""

PRODUCTION_VERSION = "v2.0_baseline"

# Dictionary untuk menampung versi parameter override
# Key: Nama/Versi Eksperimen
# Value: Dictionary override parameter (sesuai key settings.yaml / flat key)
EXPERIMENT_VERSIONS = {
    "v2.0_baseline": {},
    "v2.1_higher_gap": {
        "min_recommendation_gap": 0.75
    },
    "v2.2_no_temp_bonus": {
        "weather_thresholds.temp_hot_bonus": 0.0,
        "weather_thresholds.temp_cold_penalty": 0.0
    },
    # Hipotesis: bonus/penalti suhu mungkin sudah "dihargai" pasar Polymarket
    # (line sudah mempertimbangkan prakiraan cuaca), sehingga menambah modifier
    # di atasnya berisiko double counting terhadap informasi yang sudah efisien
    # di pasar. Diuji mulai 06 Juli 2026.

    "v2.3_coors_boost": {
        "override_pf": 118
    },
    # Hipotesis: Park Factor Coors saat ini (113, PF asli di park_factors.py)
    # masih underestimate run aktual (dari analisis historis, deviasi rata-rata
    # -3.37 run). Menguji PF lebih tinggi (118) khusus untuk game di Coors Field
    # (override_pf hanya berlaku saat team_id home == 115, sudah ada logikanya
    # di calculate_park_score()). Diuji mulai 06 Juli 2026.

    "v2.4_wind_boost": {
        "weather_thresholds.wind_outward_cap": 1.2,
        "weather_thresholds.wind_coefficient_per_mph": 0.06
    },
    # Hipotesis: efek angin outward kencang (mis. Wrigley Field) masih
    # underestimate run aktual (dari analisis historis, deviasi rata-rata -4.91
    # run pada game angin outward kencang). Menguji cap dan koefisien lebih
    # tinggi. Diuji mulai 06 Juli 2026.
}
