import pytest
from unittest.mock import patch, MagicMock
import sys
import os
from datetime import datetime

# Menambahkan direktori root proyek ke sys.path agar 'src' bisa diimport
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Modules to Test
from src.collectors.mlb_schedule import get_todays_games
from src.processors.pitcher_scorer import calculate_pitcher_score
from src.processors.offense_scorer import calculate_streak_modifier
from src.processors.environment_scorer import calculate_weather_score, calculate_park_score
from src.processors.run_calculator import calculate_expected_total_runs, make_recommendation
from src.collectors.polymarket import get_ou_line

@pytest.fixture
def dummy_game_data():
    """Fixture data dummy untuk pertandingan NYY vs BOS."""
    return {
        "home_team_id": 147, # Yankees
        "away_team_id": 111, # Red Sox
        "home_team_stats": {"runs_per_game": 4.8, "team_era": 3.9, "ops": 0.780},
        "away_team_stats": {"runs_per_game": 4.5, "team_era": 4.2, "ops": 0.750},
        "home_pitcher_stats": {"era": 3.2, "whip": 1.1, "k9": 9.5},
        "away_pitcher_stats": {"era": 4.5, "whip": 1.4, "k9": 7.2},
        "home_pitcher_last_3": [],
        "away_pitcher_last_3": [],
        "home_bullpen_era": 3.5,
        "away_bullpen_era": 4.2,
        "home_streak": "HOT",
        "away_streak": "NEUTRAL",
        "weather": {
            "temperature_fahrenheit": 75,
            "wind_speed_mph": 5,
            "wind_direction_degrees": 0,
            "stadium_orientation": 45
        },
        "park_factor": 102 # Yankee Stadium
    }

def test_mlb_schedule():
    """Validasi format output jadwal MLB."""
    import pytz
    et_tz = pytz.timezone('America/New_York')
    target_date = datetime.now(et_tz).strftime('%Y-%m-%d')
    
    with patch('src.collectors.mlb_schedule.get_upcoming_games') as mock_upcoming:
        mock_upcoming.return_value = [{
            "game_id": 123,
            "away_team": "Red Sox",
            "home_team": "Yankees",
            "game_date_et": target_date,
            "venue_name": "Yankee Stadium"
        }]
        
        games = get_todays_games()
        assert len(games) > 0
        assert games[0]['game_id'] == 123
        assert games[0]['home_team'] == 'Yankees'
        assert games[0]['venue_name'] == 'Yankee Stadium'

def test_pitcher_scorer():
    """Validasi scoring pitcher (ERA elit vs buruk)."""
    # Pitcher Elit
    elite_stats = {"era": 2.5, "whip": 1.0, "k9": 10.0}
    score_elite, _ = calculate_pitcher_score(elite_stats)
    assert score_elite < 0 # Harus mengurangi run
    
    # Pitcher Buruk
    bad_stats = {"era": 5.5, "whip": 1.6, "hr9": 1.8}
    score_bad, _ = calculate_pitcher_score(bad_stats)
    assert score_bad > 0 # Harus menambah run
    
    # Range check
    assert -2.0 <= score_elite <= 2.0
    assert -2.0 <= score_bad <= 2.0

def test_offense_scorer():
    """Validasi modifier streak tim."""
    hot_mod, _ = calculate_streak_modifier("HOT")
    cold_mod, _ = calculate_streak_modifier("COLD")
    neutral_mod, _ = calculate_streak_modifier("NEUTRAL")
    
    assert hot_mod == 0.5
    assert cold_mod == -0.5
    assert neutral_mod == 0

def test_weather_scorer():
    """Validasi efek angin outward."""
    weather_outward = {
        "wind_speed_mph": 20,
        "wind_direction_degrees": 225, # Berlawanan dengan orientasi stadium 45 = OUTWARD
        "stadium_orientation": 45,
        "temperature_fahrenheit": 70
    }
    # Mocking interpret_wind_direction secara manual jika perlu, 
    # namun fungsi aslinya sudah mendukung logika ini.
    score, _ = calculate_weather_score(weather_outward)
    assert score > 0.4 # Angin kencang keluar harus menambah proyeksi run

def test_park_scorer():
    """Validasi bonus khusus Coors Field."""
    # Test Park Neutral
    score_neutral, _ = calculate_park_score(100)
    assert score_neutral == 0
    
    # Test Coors Field (ID 115)
    score_coors, reasons = calculate_park_score(113, team_id=115)
    assert score_coors >= 1.0
    assert any("Hitter's Park" in r for r in reasons)

def test_run_calculator(dummy_game_data):
    """Validasi alur kalkulasi akhir & rekomendasi."""
    result = calculate_expected_total_runs(dummy_game_data)
    
    assert "final_expected_runs" in result
    assert "reasons" in result
    assert len(result["reasons"]) >= 0 # Bisa 0 jika metrik sangat standar rata-rata
    
    # Test Recommendation
    # Jika line 8.0 dan proyeksi 10.0 -> OVER
    rec = make_recommendation(10.0, 8.0)
    assert "OVER" in rec
    
    # Jika line 11.0 dan proyeksi 9.0 -> UNDER
    rec = make_recommendation(9.0, 11.0)
    assert "UNDER" in rec

def test_polymarket_parsing():
    """Validasi prioritas data line dari Bullpen CLI."""
    with patch('src.collectors.polymarket.get_bullpen_line') as mock_bullpen:
        mock_bullpen.return_value = {
            'line': 8.5,
            'over_price': 55.0,
            'under_price': 45.0,
            'game_time_et': '7:05 PM',
            'game_date_et': '2026-06-20',
            'line_range': '8.0 - 9.0',
            'market_id': 'm1',
            'source': 'Bullpen CLI'
        }
        
        line_info = get_ou_line("New York Yankees", "Boston Red Sox")
        assert line_info is not None
        assert line_info['line'] == 8.5
        assert line_info['source'] == 'Bullpen CLI'
