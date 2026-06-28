"""
Modul untuk menganalisis Streak (Hot/Cold) dan Momentum secara mendalam.
Ini merupakan peningkatan (Enhancement) dari deteksi streak sederhana di Phase 1.
"""

def detect_offensive_streak(last_10_games):
    """
    Menganalisis performa offense berdasarkan 10 game terakhir menggunakan moving averages.
    
    Args:
        last_10_games (list): Data game dari API (diurutkan terbaru ke terlama).
        
    Returns:
        dict: Hasil analisis meliputi streak_type, streak_length, momentum_direction, confidence_level.
    """
    if not last_10_games or len(last_10_games) < 7:
        return {"type": "NEUTRAL", "momentum": "FLAT", "score": 0.0}

    # Ekstraksi Batting Average per game riil: hits / atBats (Abaikan game tanpa data)
    ba_history = []
    for g in last_10_games:
        stat = g.get("stat", {})
        hits = stat.get("hits")
        ab = stat.get("atBats")
        try:
            if hits is not None and ab is not None:
                hits = int(hits)
                ab = int(ab)
                if ab > 0:
                    ba_history.append(hits / ab)
        except (ValueError, TypeError):
            pass

    if len(ba_history) < 7:
        return {"type": "NEUTRAL", "momentum": "FLAT", "score": 0.0}

    # Hitung rata-rata untuk interval yang berbeda (dari terbaru)
    avg_3 = sum(ba_history[:3]) / 3
    avg_5 = sum(ba_history[:5]) / 5
    avg_7 = sum(ba_history[:7]) / 7

    # Deteksi Tipe Streak (Berdasarkan 7 game terakhir sesuai PRD)
    streak_type = "NEUTRAL"
    base_score = 0.0
    if avg_7 >= 0.280:
        streak_type = "HOT"
        base_score = 0.4
    elif avg_7 <= 0.220:
        streak_type = "COLD"
        base_score = -0.4

    # Deteksi Momentum (Apakah performa membaik atau memburuk baru-baru ini?)
    momentum = "FLAT"
    momentum_mod = 0.0
    
    if avg_3 > avg_7 + 0.020:
        momentum = "IMPROVING"
        momentum_mod = 0.2
    elif avg_3 < avg_7 - 0.020:
        momentum = "DECLINING"
        momentum_mod = -0.2

    final_score = round(base_score + momentum_mod, 2)
    # Batasi score maksimum
    final_score = max(min(final_score, 0.6), -0.6)

    return {
        "type": streak_type,
        "momentum": momentum,
        "score": final_score,
        "avg_7": round(avg_7, 3),
        "avg_3": round(avg_3, 3)
    }

def detect_pitcher_form(pitcher_season_stats, last_3_starts):
    """
    Menganalisis apakah pitcher sedang dalam kondisi peak atau struggle.
    
    Args:
        pitcher_season_stats (dict): Statistik full season.
        last_3_starts (list): Data log 3 game terakhir.
        
    Returns:
        dict: Analisis form pitcher dan modifier score.
    """
    if not pitcher_season_stats or not last_3_starts or len(last_3_starts) < 2:
        return {"form": "UNKNOWN", "score": 0.0}

    season_era = pitcher_season_stats.get("era")
    if not season_era:
        return {"form": "UNKNOWN", "score": 0.0}
    
    try:
        season_era = float(season_era)
    except:
        return {"form": "UNKNOWN", "score": 0.0}

    # Hitung ERA perkiraan di 3 start terakhir (Kasaran dari IP dan asumsi standard runs)
    # Karena API gameLog pitching punya struktur kompleks, kita fokus pada efisiensi IP vs Pitch Count
    # Jika efisiensi menurun (Pitch banyak, IP sedikit), form buruk.
    
    total_pitches = sum([int(s.get("pitch_count", 0)) for s in last_3_starts])
    total_ip = sum([float(s.get("innings_pitched", 0)) for s in last_3_starts])
    
    if total_ip == 0:
        return {"form": "STRUGGLING", "score": 0.4} # Score positif = banyak run = pitcher buruk

    pitches_per_ip = total_pitches / total_ip
    
    score = 0.0
    form = "NORMAL"
    reasons = []

    # Standar liga: ~16 pitches per inning. 
    # > 19 berarti sangat struggle/inefisien. < 14 berarti sangat tajam/efisien.
    if pitches_per_ip > 19.0:
        form = "STRUGGLING"
        score = 0.3
        reasons.append("Inefisien di 3 start terakhir (Pitches/IP tinggi)")
    elif pitches_per_ip < 14.0:
        form = "PEAK"
        score = -0.3
        reasons.append("Sangat efisien di 3 start terakhir (Pitches/IP rendah)")

    return {
        "form": form,
        "score": score,
        "pitches_per_ip": round(pitches_per_ip, 1),
        "reasons": reasons
    }

def calculate_momentum_score(offensive_streak_data, pitcher_form_data):
    """
    Menggabungkan hasil analisis offense dan pitcher menjadi satu nilai momentum.
    Score positif (+) berarti mendorong ke arah OVER.
    Score negatif (-) berarti mendorong ke arah UNDER.
    """
    off_score = offensive_streak_data.get("score", 0.0)
    pit_score = pitcher_form_data.get("score", 0.0)
    
    total_momentum = round(off_score + pit_score, 2)
    return max(min(total_momentum, 1.0), -1.0)
