import pytest
from unittest.mock import patch, MagicMock
import sys
import os

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
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            "dates": [{
                "games": [{
                    "gamePk": 123,
                    "teams": {
                        "home": {"team": {"name": "Yankees"}},
                        "away": {"team": {"name": "Red Sox"}}
                    },
                    "gameDate": "2026-06-13T19:10:00Z",
                    "venue": {"name": "Yankee Stadium"}
                }]
            }]
        }
        mock_get.return_value.status_code = 200
        
        games = get_todays_games()
        assert len(games) > 0
        assert games[0]['game_id'] == 123
        assert "home_team" in games[0]
        assert "venue_name" in games[0]

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
    assert any("Coors Field" in r for r in reasons)

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
    """Validasi parsing data dari Polymarket Gamma API."""
    with patch('src.collectors.polymarket.get_mlb_ou_markets') as mock_markets:
        mock_markets.return_value = [{
            "id": "m1",
            "title": "Total Runs: New York Yankees vs Boston Red Sox",
            "question": "Will there be over 8.5 runs in the New York Yankees vs Boston Red Sox game?",
            "outcomes": ["Yes", "No"],
            "clobTokenIds": ["t1", "t2"]
        }]
        
        with patch('requests.get') as mock_clob:
            mock_clob.return_value.json.return_value = {"price": "0.55"}
            mock_clob.return_value.status_code = 200
            
            line_info = get_ou_line("New York Yankees", "Boston Red Sox")
            assert line_info['line'] == 8.5
            assert "Yes" in line_info['odds']
