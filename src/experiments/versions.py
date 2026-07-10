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

    "v3.0_bullpen_fatigue": {
        "enable_bullpen_fatigue": True
    },

    "v3.1_dynamic_variance_gap": {
        "enable_dynamic_gap": True
    },

    "v3.2_reduced_hr_risk": {
        "hr9_risk_modifier": 0.25
    },
    # Hipotesis: dari analisis 169 prediksi OVER historis, modifier "Rawan
    # Home Run" (+0.5 run) muncul jauh lebih sering di prediksi yang SALAH
    # (20.5%) dibanding yang BENAR (7.0%) -- indikasi HR/9 rentan noise
    # sample kecil dan mungkin overweighted. Menguji bobot setengahnya
    # (0.25). Diuji mulai 09 Juli 2026.

    "v3.3_reduced_weather": {
        "weather_thresholds.wind_coefficient_per_mph": 0.02,
        "weather_thresholds.wind_outward_cap": 0.4,
        "weather_thresholds.wind_inward_cap": -0.4,
        "weather_thresholds.temp_hot_bonus": 0.15,
        "weather_thresholds.temp_cold_penalty": -0.15,
    },
    # Hipotesis: dari analisis 169 prediksi OVER historis, game dengan data
    # cuaca TIDAK TERSEDIA justru punya win rate lebih tinggi (20.9% dari
    # yang BENAR) dibanding saat cuaca tersedia dan dipakai (7.2% dari yang
    # SALAH) -- indikasi modifier cuaca saat ini mungkin menambah noise,
    # bukan sinyal. Menguji separuh bobot semua threshold cuaca. Diuji
    # mulai 09 Juli 2026.

    "v4.0_recalibrated_baseline": {
        "hr9_risk_modifier": 0.25,
        "whip_high_modifier": 0.15,
        "k9_low_modifier": 0.15,
        "control_elite_modifier": -0.15,
        "short_innings_run_modifier": 0.0,
        "enable_dynamic_gap": True,
    },
    # RECALIBRATION MENYELURUH berdasarkan analisis residual |prediksi-aktual|
    # dari 51 game baseline (09 Juli 2026): WHIP tinggi, K/9 rendah, Kontrol
    # elit, dan Rawan Home Run terbukti berkorelasi dengan error LEBIH BESAR
    # dari rata-rata saat aktif -- bobotnya diturunkan proporsional (dibulatkan
    # setengahnya). "Inning pendek" (bullpen exposure, n=33, sample besar)
    # dialihkan dari modifier run pasti menjadi pemicu volatility_score
    # (perlu enable_dynamic_gap=True supaya efeknya berlaku ke keputusan).
    # Modifier yang terbukti RELIABLE (Kontrol buruk, Pitcher's Park, Supresi
    # Home Run elit, Home/Away Momentum, Inning panjang) SENGAJA TIDAK diubah.
    # Diuji mulai 10 Juli 2026 -- kandidat baseline baru, BELUM untuk
    # menggantikan produksi sampai terbukti lebih baik dengan sample memadai.
}
