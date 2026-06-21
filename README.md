# ⚾ MLB Bullpen.fi AI Bot

> **Prediksi Over/Under Baseball berbasis Data (Fokus Bullpen.fi)**

MLB Bullpen.fi AI Bot adalah asisten cerdas yang dirancang untuk Vibe Coders, Indie Developers, dan Bettors amatir. Bot ini secara otomatis membaca pasar Over/Under dari Bullpen.fi (dengan fallback ke Polymarket dan The Odds API), menarik statistik lanjutan dari MLB, meramu data cuaca dan stadion, lalu memberikan rekomendasi taruhan dengan *Edge* tertinggi.
 Seluruh ekosistem bot ini dibangun **100% menggunakan API dan tools gratis**, sehingga Anda tidak perlu mengeluarkan biaya berlangganan data bulanan.

---

## ✨ Fitur Utama
*   **Fully Automated:** Berjalan 24/7 di latar belakang, menarik jadwal harian, memantau *line movement*, dan merekap hasil kemenangan secara otomatis.
*   **Advanced Sabermetrics:** Tidak hanya menggunakan ERA/AVG, bot ini mengorek data FIP, wRC+, *Hard Hit %*, hingga beban kerja *bullpen* dari FanGraphs & MLB Stats.
*   **Context-Aware:** Memasukkan *Park Factor* (cth: tipisnya udara Coors Field) dan vektor cuaca (arah/kecepatan angin) sebagai *modifier* krusial dalam kalkulasi skor.
*   **Smart Alerts:** Terintegrasi dengan Telegram & Discord. Dilengkapi *Anti-Spam* agar Anda hanya menerima notifikasi saat bot menemukan peluang `HIGH Confidence`.
*   **Beautiful Dashboard:** Visualisasi tingkat lanjut menggunakan Streamlit & Plotly (Waterfall Charts, Perbandingan Lineup, dan Historis Win Rate).
*   **Self-Evaluating:** Menyimpan riwayat prediksi di SQLite dan secara otomatis mencocokkan skor aktual keesokan harinya untuk menghitung akurasi bot secara *real-time*.

---

## 💻 Requirements
*   **OS:** Windows, macOS, atau Linux
*   **Python:** Versi 3.10 hingga 3.12 (Sangat disarankan untuk kompatibilitas Pandas/Streamlit)
*   **Koneksi Internet:** Stabil untuk keperluan *scraping* dan akses REST API.

---

## 🚀 Instalasi (Step-by-Step)

1. **Clone Repository ini**
   ```bash
   git clone https://github.com/yourusername/mlb-polymarket-bot.git
   cd mlb-polymarket-bot
   ```

2. **Install Dependencies**
   *Sangat disarankan menggunakan Virtual Environment (`venv`).*
   ```bash
   pip install -r requirements.txt
   ```

3. **Konfigurasi Environment**
   Salin template `.env.example` menjadi file baru bernama `.env`. Buka file `.env` dan isi token yang diperlukan:
   *   *(Opsional namun direkomendasikan)* Isi `ODDS_API_KEY` (gratis) sebagai *fallback* jika pasar Polymarket sedang kosong.
   *   *(Opsional)* Isi token Telegram/Discord untuk menyalakan notifikasi.

4. **Jalankan untuk Pertama Kali (Manual Test)**
   ```bash
   python main.py
   ```
   Bot akan menginisialisasi database SQLite di folder `data/mlb_bot.db` dan mencetak analisis hari ini di terminal Anda.

---

## 🚀 Cara Menjalankan Bot

### Mode Otomatis 24/7 (Rekomendasi Utama)
Jalankan ini untuk operasional harian. Bot akan analisis, kirim Telegram, dan
catat prediksi secara otomatis tanpa perlu buka dashboard.
```bash
python run_bot.py
```

### Mode Dashboard (Review Manual)
Buka ini HANYA saat ingin melihat grafik akurasi dan history prediksi.
Tutup setelah selesai review agar tidak memberatkan laptop.
```bash
python run_dashboard.py
```
→ Buka browser: http://localhost:8501
→ Setelah selesai: tekan Ctrl+C di terminal untuk menutup

### ⚠️ Catatan Penting
- Jangan jalankan run_bot.py dan run_dashboard.py di terminal yang SAMA
- Jika ingin keduanya jalan bersamaan, buka DUA terminal terpisah
- Dashboard hanya membaca database, tidak mempengaruhi bot sama sekali

### Mode Lainnya (Terminal / Manual)
*   **Analisis 1 Game Spesifik (Gunakan Game ID):**
    ```bash
    python main.py --game "824428"
    ```
*   **Mode Debug / Verbose (Tampilkan Alasan Skip):**
    ```bash
    python main.py --verbose
    ```
*   **Jalankan Backtesting Masa Lalu (Database):**
    ```bash
    python src/backtesting/backtest_engine.py
    ```

---

## 🔔 Setup Notifikasi (Opsional)

**Telegram Bot:**
1. Buka aplikasi Telegram dan cari **@BotFather**.
2. Kirim perintah `/newbot` dan ikuti langkah pembuatan bot.
3. Salin `HTTP API Token` yang diberikan dan tempelkan ke `.env` di variabel `TELEGRAM_BOT_TOKEN`.
4. Cari bot **@userinfobot** di Telegram untuk mendapatkan `Chat ID` Anda, lalu masukkan ke `TELEGRAM_CHAT_ID`.

**Discord Webhook:**
1. Buka server Discord Anda -> *Server Settings* -> *Integrations* -> *Webhooks*.
2. Buat Webhook baru, pilih channel target, dan klik *Copy Webhook URL*.
3. Tempelkan URL tersebut ke `.env` di variabel `DISCORD_WEBHOOK_URL`.

---

## 🧠 Penjelasan Faktor Analisis (Otak Bot)

Bot ini memecah probabilitas skor menjadi 15+ faktor dengan bobot yang bervariasi:
1.  **Faktor Pitcher (~40%):** Membandingkan FIP (Fielding Independent Pitching) vs ERA, K/9 (kemampuan Strikeout), dan kerentanan terhadap Home Run (HR/9). Bot juga akan memberikan *penalty* jika starter terlihat kelelahan (pitch count > 100 berturut-turut).
2.  **Faktor Offense (~30%):** Menganalisis wRC+ dan tren Batting Average (Mendeteksi apakah sebuah tim sedang *HOT* atau *COLD* dalam 7 game terakhir). Bot menyoroti efisiensi saat ada *Runner in Scoring Position* (RISP).
3.  **Kondisi Lingkungan (~15%):** Mengambil data arah angin secara *real-time*. Angin *OUTWARD* kencang (>15mph) akan memicu prediksi OVER, sementara angin *INWARD* di stadion bersuhu dingin akan memicu prediksi UNDER. *Park Factors* (seperti Coors Field) juga menormalisasi standar kalkulasi.
4.  **Konteks Tambahan (~15%):** Kekuatan ERA dari Bullpen (sangat vital di inning akhir), kelelahan jadwal tim tandang, dan pergerakan garis taruhan (*Line Movement*) Polymarket.

---

## ⚠️ Disclaimer

> **Bot ini dibangun murni untuk tujuan edukasi, pemrograman (Vibe Coding), dan eksperimen Data Science. Ini BUKAN merupakan saran finansial (Financial Advice).**
> Bisbol adalah olahraga dengan variansi yang sangat tinggi. Sistem AI sehebat apa pun (termasuk bot ini) dirancang untuk mencari **"Edge" statistik sebesar 52-55%** dalam jangka panjang, bukan kepastian 100%. Segala bentuk kerugian finansial akibat penggunaan data dari bot ini sepenuhnya merupakan tanggung jawab pengguna. **Bertaruhlah dengan bijak dan gunakan uang "dingin".**

---

## 🗺️ Roadmap Proyek

- [x] **Phase 1 (MVP):** Kolektor data dasar, API Integrasi, Terminal Output rapi.
- [x] **Phase 2 (Enhanced):** Integrasi Cuaca Open-Meteo, Scraper FanGraphs Advanced Stats, Discord Sender.
- [x] **Phase 3 (Intelligence):** SQLite Storage, Streak Detector, Real-time Result Fetcher, Backtesting Engine.
- [x] **Phase 4 (Automation):** Auto Runner / Scheduler 24/7, Smart Anti-Spam Alerts, Streamlit Visual Dashboard.
- [ ] **Phase 5 (Future):** *Machine Learning Regression* pengganti bobot heuristik statis, Notifikasi via Twitter/X.
