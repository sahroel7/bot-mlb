# Product Requirements Document (PRD)
## MLB Polymarket Over/Under Prediction AI Bot

**Versi:** 1.0  
**Tanggal:** Juni 2026  
**Status:** Draft  
**Tipe Proyek:** Free & Open Source AI Bot

---

## 1. RINGKASAN EKSEKUTIF

### 1.1 Visi Produk
Membangun AI Bot yang sepenuhnya gratis yang mampu membaca prediksi Over/Under dari Polymarket untuk pertandingan MLB (Major League Baseball), menganalisis faktor-faktor kritis yang memengaruhi skor, dan memberikan rekomendasi berbasis data kepada pengguna.

### 1.2 Problem Statement
Bettor dan analis olahraga menghabiskan berjam-jam secara manual mengumpulkan data:
- Odds Over/Under dari Polymarket
- Statistik pitcher dan batter
- Kondisi cuaca, venue, dan faktor kontekstual lainnya

Bot ini mengotomatiskan seluruh proses tersebut menjadi satu rekomendasi yang actionable.

### 1.3 Target Pengguna
- Vibe coder / indie developer yang ingin tool gratis
- Sports bettor pemula hingga menengah
- Analis olahraga amatir yang ingin data-driven insight

---

## 2. LINGKUP PRODUK (SCOPE)

### 2.1 IN SCOPE ✅
- Membaca pasar Over/Under MLB dari Polymarket API (public)
- Mengumpulkan data statistik MLB dari sumber gratis
- Menganalisis 15+ faktor penentu skor pertandingan
- Memberikan rekomendasi Over atau Under per game
- Output dalam format teks (terminal / Discord bot / Telegram bot)
- Semua komponen menggunakan tools & API gratis

### 2.2 OUT OF SCOPE ❌
- Prediksi pemenang pertandingan (Moneyline)
- Prediksi run spread / handicap
- Olahraga selain MLB
- Eksekusi otomatis taruhan
- Fitur berbayar / premium tier
- Data real-time sub-1 menit (terlalu mahal)

---

## 3. PEMAHAMAN DOMAIN: FAKTOR PENENTU SKOR MLB

> **Catatan Penting:** Bagian ini adalah "otak" dari bot. Semakin akurat bot memahami faktor-faktor ini, semakin baik prediksinya.

### 3.1 FAKTOR PITCHER (Bobot: ~40% dari total analisis)

#### 3.1.1 Starting Pitcher — Metrik Utama
| Metrik | Deskripsi | Relevansi O/U |
|--------|-----------|---------------|
| ERA (Earned Run Average) | Rata-rata run yang diberikan per 9 inning | ERA tinggi → cenderung OVER |
| FIP (Fielding Independent Pitching) | ERA yang tidak dipengaruhi pertahanan | Lebih prediktif dari ERA |
| WHIP (Walks + Hits per Inning) | Seberapa banyak baserunner diberikan | WHIP > 1.4 → risiko OVER naik |
| K/9 (Strikeout per 9 inning) | Kemampuan mematikan batter | K/9 tinggi → cenderung UNDER |
| BB/9 (Walk per 9 inning) | Kontrol lemparan | BB/9 > 3 → tekanan OVER |
| HR/9 (Home Run per 9 inning) | Kerentanan terhadap home run | HR/9 > 1.5 → red flag OVER |
| Ground Ball % | Rasio bola tanah vs fly ball | GB% rendah = fly ball pitcher = lebih banyak HR |
| Hard Hit % | Persentase bola yang dipukul keras | Hard Hit > 40% → cenderung OVER |
| Spin Rate (Fastball) | Rotasi bola per menit | Spin rendah = bola mudah dipukul |

#### 3.1.2 Kelelahan & Beban Pitcher
- **Days Rest:** Pitcher yang istirahat < 4 hari performanya turun signifikan
- **Pitch Count 2 start terakhir:** Jika > 100 pitch dua kali berturut-turut, efisiensi menurun
- **IP (Innings Pitched) per start:** Starter yang biasa hanya 5 inning → bullpen lebih banyak dipakai → peluang run lebih tinggi

#### 3.1.3 Bullpen Quality
- Bullpen ERA tim → starter early exit = bulpen tampil → run lebih banyak masuk
- Save% tidak relevan, yang relevan: **Leverage Index** dan **Inherited Runner %**

---

### 3.2 FAKTOR OFFENSE / BATTER (Bobot: ~30%)

#### 3.2.1 Tim Offense Metrics
| Metrik | Deskripsi | Relevansi O/U |
|--------|-----------|---------------|
| wRC+ (Weighted Runs Created+) | Efisiensi mencetak run vs liga | wRC+ > 110 = lineup berbahaya |
| OPS (OBP + SLG) | Gabungan kemampuan on-base & power | OPS > .800 → OVER pressure |
| ISO (Isolated Power) | Murni power hitting | ISO > .180 → HR threat |
| BABIP | Batting avg on balls in play | Tinggi = sedang beruntung / dalam form baik |
| K% Tim | Persentase strikeout tim | K% tinggi vs pitcher strikeout = UNDER signal |
| BB% Tim | Persentase walk diterima tim | BB% tinggi = sabar, bisa naikkan run |
| Runners in Scoring Position (RISP) AVG | AVG saat ada runner di 2B/3B | Menentukan berapa run terkonversi |

#### 3.2.2 Platoon Advantage (Matchup)
- Batter kidal (LHH) vs pitcher kidal (LHP) → batter dirugikan
- Batter kidal (LHH) vs pitcher tangan kanan (RHP) → batter diuntungkan
- Hitung berapa % lineup punya platoon advantage → semakin banyak = run lebih tinggi

#### 3.2.3 Recent Form (Hot/Cold Streak)
- Tim dengan streak 5+ game di atas .300 BA = "hot" → OVER signal
- Tim dengan streak 5+ game di bawah .220 BA = "cold" → UNDER signal

---

### 3.3 FAKTOR KONDISI LAPANGAN & CUACA (Bobot: ~15%)

#### 3.3.1 Ballpark Factor (Park Factor)
Setiap stadion MLB punya karakteristik berbeda yang secara historis memengaruhi run:

| Kategori | Contoh Stadion | Efek |
|----------|---------------|------|
| **Hitter's Park** (PF > 105) | Coors Field (Denver), Great American Ball Park | Lebih banyak run, OVER lebih sering masuk |
| **Pitcher's Park** (PF < 95) | Oracle Park (SF), Petco Park (SD) | Lebih sedikit run, UNDER lebih sering masuk |
| **Neutral** (PF 95-105) | Majority of parks | Netral |

> **Coors Field exception:** Ketinggian Denver (5.280 kaki) membuat bola terbang lebih jauh. Selalu naikkan proyeksi 1-2 run saat di Coors.

#### 3.3.2 Kondisi Cuaca
| Faktor | Efek terhadap Skor |
|--------|-------------------|
| Angin > 15 mph ke arah LF/RF/CF (keluar lapangan) | +0.5 hingga +1.5 run → push OVER |
| Angin ke dalam lapangan (inward) | -0.5 hingga -1 run → push UNDER |
| Suhu udara > 85°F | Bola lebih "hidup", terbang lebih jauh → OVER |
| Suhu < 50°F | Bola kurang elastis, lebih sedikit HR → UNDER |
| Kelembaban tinggi | Bola sedikit lebih berat → sedikit kurangi jarak |
| Hujan/Drizzle | Grip pitcher terganggu → lebih banyak walk/hit → OVER |

> **API Cuaca Gratis:** Open-Meteo.com atau wttr.in — keduanya tidak butuh API key

---

### 3.4 FAKTOR HEAD-TO-HEAD & KONTEKSTUAL (Bobot: ~10%)

#### 3.4.1 Sejarah Pertemuan
- H2H total run 10 game terakhir antara dua tim ini
- H2H dengan pitcher yang sama (jika pitcher sudah pernah duel)

#### 3.4.2 Situasi Permainan
| Faktor | Pengaruh |
|--------|----------|
| Doubleheader (Game 1 vs Game 2) | Game 2 sering pakai opener/bullpen → lebih banyak run |
| Series finale | Tim sering pakai opener di hari terakhir series |
| Road trip panjang (>7 hari) | Kelelahan tim tandang → offense menurun |
| Home stand awal musim | Boost moral dan offense |

#### 3.4.3 Lineup Changes
- Apakah cleanup hitter (posisi 3-4-5) absen?
- Posisi pemain (starter reguler vs cadangan)
- Source: Baseball Reference, MLB.com official lineup

---

### 3.5 FAKTOR PASAR (Bobot: ~5%)

#### 3.5.1 Line Movement Polymarket
- Jika odds OVER bergerak naik signifikan dalam 2 jam terakhir → "sharp money" masuk ke OVER
- Jika total (angka Over/Under) dinaikkan sportsbook → market ekspektasi run naik
- Uang besar di UNDER + starter elit yang confirm = konfirmasi UNDER

---

## 4. ARSITEKTUR SISTEM

### 4.1 Komponen Utama

```
┌─────────────────────────────────────────────────┐
│                  AI BOT FLOW                     │
├─────────────────────────────────────────────────┤
│                                                   │
│  [1. DATA COLLECTOR]                             │
│     ├── Polymarket API (odds + market data)      │
│     ├── MLB Stats API (stats.mlb.com) — GRATIS   │
│     ├── Baseball Reference / FanGraphs scraping  │
│     └── Open-Meteo API (cuaca) — GRATIS          │
│                 ↓                                 │
│  [2. DATA PROCESSOR]                             │
│     ├── Normalisasi semua metrik                 │
│     ├── Hitung skor bobot per faktor             │
│     └── Kalkulasi "Expected Total Runs"          │
│                 ↓                                 │
│  [3. AI ANALYZER]                                │
│     ├── Bandingkan Expected Runs vs Polymarket   │
│     │   line                                     │
│     ├── Identifikasi edge (selisih > threshold)  │
│     └── Generate reasoning teks                  │
│                 ↓                                 │
│  [4. OUTPUT MODULE]                              │
│     ├── Terminal / CLI output                    │
│     ├── Telegram Bot (opsional)                  │
│     └── Discord Webhook (opsional)               │
└─────────────────────────────────────────────────┘
```

### 4.2 Data Sources (Semua Gratis)

| Sumber | Data Yang Diambil | Metode Akses |
|--------|------------------|--------------|
| `statsapi.mlb.com` | Lineup, pitcher stats, schedule | REST API, no key |
| `baseballreference.com` | Historical stats, park factors | Web scraping (BeautifulSoup) |
| `polymarket.com` | Odds Over/Under MLB | REST API / CLOB API |
| `open-meteo.com` | Cuaca per kota | REST API, no key |
| `fangraphs.com` | Advanced stats (FIP, wRC+, BABIP) | Web scraping |

> **Stack Teknologi Rekomendasi:** Python 3.10+, `requests`, `beautifulsoup4`, `pandas`, `openai` (gratis dengan key), atau `ollama` (100% lokal gratis)

---

## 5. LOGIKA SCORING BOT

### 5.1 Algoritma Kalkulasi Expected Runs

```
Base Run Projection = (Tim A avg runs/game + Tim B avg runs allowed/game) / 2

Modifiers:
  + Pitcher Quality Score  (−2.0 to +2.0)
  + Park Factor Score      (−1.5 to +1.5)
  + Weather Score          (−1.0 to +1.0)
  + Offense Hot/Cold       (−0.5 to +0.5)
  + Platoon Advantage      (−0.3 to +0.3)
  + H2H Historical         (−0.3 to +0.3)

Final Expected Runs = Base + Sum(Modifiers)
```

### 5.2 Decision Logic

```python
if final_expected_runs > (polymarket_line + 0.5):
    recommendation = "OVER ✅"
    confidence = calculate_confidence(gap)
elif final_expected_runs < (polymarket_line - 0.5):
    recommendation = "UNDER ✅"  
    confidence = calculate_confidence(gap)
else:
    recommendation = "NO BET / SKIP ⚠️"
    confidence = "LOW"
```

### 5.3 Confidence Level
| Gap vs Line | Confidence |
|------------|------------|
| > 1.5 run | 🔥 HIGH (80%+) |
| 0.5 – 1.5 run | ⚡ MEDIUM (60-79%) |
| < 0.5 run | ⚠️ LOW — SKIP |

---

## 6. FORMAT OUTPUT BOT

### 6.1 Contoh Output Terminal
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏟️  NYY @ BOS | 13 Jun 2026 | 19:10 ET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Polymarket O/U Line  : 9.0
🎯 Bot Expected Runs    : 10.3
📈 Recommendation       : OVER ✅
🔥 Confidence           : HIGH (82%)

📋 KEY FACTORS:
  ⚾ NYY SP: Carlos Rodon  | ERA 4.21 | FIP 3.98 | WHIP 1.38
  ⚾ BOS SP: Tanner Houck  | ERA 3.87 | FIP 3.71 | WHIP 1.22
  🌡️  Cuaca: 79°F, Angin 18mph →→ ke CF (keluar)  [+1.2 run]
  🏟️  Fenway Park Factor: 108 (Hitter-friendly)   [+0.8 run]
  💪 BOS Offense Hot (7-game): .301 BA streak      [+0.5 run]
  ⚠️  NYY Bullpen ERA: 4.67 (lemah)               [+0.4 run]

💰 Polymarket Link: polymarket.com/game/NYY-BOS-06-13
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 7. BATASAN DAN DISCLAIMER

### 7.1 Batasan Teknis
- Data lineup resmi baru tersedia ~2 jam sebelum game
- Cuaca bisa berubah mendadak (terutama outdoor stadium)
- Polymarket odds bergerak dinamis — bot harus refresh tiap 30 menit
- Scraping FanGraphs/Baseball Reference bisa kena rate-limit → tambahkan `sleep()` dan retry logic

### 7.2 Batasan Prediksi
- Bot **bukan oracle** — akurasi target realistis: 54-58% win rate (cukup untuk value betting)
- Injury pemain kunci yang diumumkan < 1 jam sebelum game sulit dideteksi
- "Hot hand" di baseball bisa berakhir kapan saja

### 7.3 Disclaimer
> Bot ini dibuat untuk tujuan edukasi dan analisis data. Segala keputusan bertaruh adalah tanggung jawab pengguna sepenuhnya.

---

## 8. ROADMAP PENGEMBANGAN

### Phase 1 — MVP (Minggu 1-2)
- [ ] Polymarket scraper untuk MLB O/U lines
- [ ] MLB Stats API integration (lineup + starter)
- [ ] Kalkulasi dasar Expected Runs
- [ ] Terminal output

### Phase 2 — Enhanced (Minggu 3-4)
- [ ] Integrasi cuaca (Open-Meteo)
- [ ] Park Factor database
- [ ] FanGraphs scraper (FIP, wRC+)
- [ ] Platoon advantage calculator

### Phase 3 — Intelligence (Bulan 2)
- [ ] Backtesting system (test 500 game historis)
- [ ] Confidence calibration berdasarkan backtest
- [ ] Telegram / Discord output
- [ ] Streak & hot/cold detector

### Phase 4 — Automation (Bulan 3)
- [ ] Scheduler harian (cron job)
- [ ] Alert sistem saat confidence HIGH
- [ ] Dashboard sederhana (Streamlit — gratis)

---

## 9. TECH STACK REKOMENDASI (FULL FREE)

```
Language     : Python 3.10+
HTTP Client  : requests / httpx
HTML Parsing : beautifulsoup4 + lxml
Data Layer   : pandas + sqlite3 (lokal)
AI/LLM       : Ollama (lokal) atau Google Gemini API (free tier)
Scheduler    : APScheduler atau cron
Output       : python-telegram-bot / discord-webhook
Dashboard    : Streamlit (gratis hosting di streamlit.io)
Version Ctrl : GitHub (gratis)
```

---

## 10. SUCCESS METRICS

| Metrik | Target MVP | Target Phase 3 |
|--------|-----------|----------------|
| Coverage game per hari | 5+ game | Semua game MLB hari itu |
| Akurasi prediksi | > 52% | > 55% |
| Waktu analisis per game | < 30 detik | < 10 detik |
| Uptime bot | Manual run | 95%+ automated |
| False "HIGH confidence" | < 30% | < 20% |

---

*PRD ini bersifat living document — update setiap akhir phase pengembangan.*
