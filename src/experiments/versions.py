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
}
