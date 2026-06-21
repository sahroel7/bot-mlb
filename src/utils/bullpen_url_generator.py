"""
Utility to generate specific Bullpen.fi event URLs for MLB games.
Pattern: https://app.bullpen.fi/predictions/sports/mlb/event/mlb-[away]-[home]-[date]?ref=copys
"""

# Mapping of full MLB team names to Bullpen.fi short codes
TEAM_CODES = {
    "Arizona Diamondbacks": "ari",
    "Atlanta Braves": "atl",
    "Baltimore Orioles": "bal",
    "Boston Red Sox": "bos",
    "Chicago Cubs": "chc",
    "Chicago White Sox": "cws",
    "Cincinnati Reds": "cin",
    "Cleveland Guardians": "cle",
    "Colorado Rockies": "col",
    "Detroit Tigers": "det",
    "Houston Astros": "hou",
    "Kansas City Royals": "kc",
    "Los Angeles Angels": "ana",
    "Los Angeles Dodgers": "lad",
    "Miami Marlins": "mia",
    "Milwaukee Brewers": "mil",
    "Minnesota Twins": "min",
    "New York Mets": "nym",
    "New York Yankees": "nyy",
    "Oakland Athletics": "oak",
    "Philadelphia Phillies": "phi",
    "Pittsburgh Pirates": "pit",
    "San Diego Padres": "sd",
    "San Francisco Giants": "sf",
    "Seattle Mariners": "sea",
    "St. Louis Cardinals": "stl",
    "Tampa Bay Rays": "tb",
    "Texas Rangers": "tex",
    "Toronto Blue Jays": "tor",
    "Washington Nationals": "wsh",
    # Handle possible variations or short names
    "Athletics": "oak",
    "D-backs": "ari"
}

def generate_bullpen_url(away_team, home_team, game_date):
    """
    Generates a specific Bullpen.fi URL for a match.
    
    Args:
        away_team (str): Full name of the away team.
        home_team (str): Full name of the home team.
        game_date (str/datetime): Date of the game (YYYY-MM-DD or datetime object).
        
    Returns:
        str: Specific match URL or fallback to MLB main page.
    """
    try:
        # Convert team names to codes
        away_code = TEAM_CODES.get(away_team)
        home_code = TEAM_CODES.get(home_team)
        
        # Fallback if team not found
        if not away_code or not home_code:
            return "https://app.bullpen.fi/predictions/sports/mlb/games"
            
        # Format date to YYYY-MM-DD
        if hasattr(game_date, 'strftime'):
            date_str = game_date.strftime('%Y-%m-%d')
        else:
            # Assume it's a string, try to slice if it has time
            date_str = str(game_date)[:10]
            
        return f"https://app.bullpen.fi/predictions/sports/mlb/event/mlb-{away_code}-{home_code}-{date_str}?ref=copys"
        
    except Exception:
        return "https://app.bullpen.fi/predictions/sports/mlb/games"

if __name__ == "__main__":
    # Test cases
    test_games = [
        ("Houston Astros", "Kansas City Royals", "2026-06-12"),
        ("New York Yankees", "Boston Red Sox", "2026-06-13"),
        ("Los Angeles Dodgers", "Chicago White Sox", "2026-06-13"),
        ("Philadelphia Phillies", "Milwaukee Brewers", "2026-06-13"),
        ("San Diego Padres", "San Francisco Giants", "2026-06-14")
    ]
    
    print("--- Testing Bullpen URL Generator ---")
    for away, home, date in test_games:
        url = generate_bullpen_url(away, home, date)
        print(f"{away} @ {home} ({date}):\n   {url}")
