"""
Data statis Park Factors dan informasi stadion MLB.
Data didasarkan pada rata-rata 3 tahun (2022-2024) dari Baseball Savant.
"""

# Dictionary Park Factors (League Average = 100)
# Nilai > 100 menguntungkan hitter, < 100 menguntungkan pitcher.
PARK_FACTORS = {
    109: 98,   # Arizona Diamondbacks (Chase Field)
    144: 103,  # Atlanta Braves (Truist Park)
    110: 100,  # Baltimore Orioles (Oriole Park at Camden Yards)
    111: 109,  # Boston Red Sox (Fenway Park)
    112: 100,  # Chicago Cubs (Wrigley Field)
    145: 101,  # Chicago White Sox (Guaranteed Rate Field)
    113: 111,  # Cincinnati Reds (Great American Ball Park)
    114: 102,  # Cleveland Guardians (Progressive Field)
    115: 113,  # Colorado Rockies (Coors Field) - EXTREME HITTER
    116: 99,   # Detroit Tigers (Comerica Park)
    117: 100,  # Houston Astros (Minute Maid Park)
    118: 106,  # Kansas City Royals (Kauffman Stadium)
    108: 105,  # Los Angeles Angels (Angel Stadium)
    119: 101,  # Los Angeles Dodgers (Dodger Stadium)
    146: 98,   # Miami Marlins (loanDepot park)
    158: 100,  # Milwaukee Brewers (American Family Field)
    142: 98,   # Minnesota Twins (Target Field)
    121: 95,   # New York Mets (Citi Field)
    147: 102,  # New York Yankees (Yankee Stadium)
    133: 96,   # Oakland Athletics (Oakland Coliseum)
    143: 107,  # Philadelphia Phillies (Citizens Bank Park)
    134: 99,   # Pittsburgh Pirates (PNC Park)
    135: 94,   # San Diego Padres (Petco Park)
    137: 93,   # San Francisco Giants (Oracle Park)
    136: 91,   # Seattle Mariners (T-Mobile Park) - EXTREME PITCHER
    138: 97,   # St. Louis Cardinals (Busch Stadium)
    139: 97,   # Tampa Bay Rays (Tropicana Field)
    140: 104,  # Texas Rangers (Globe Life Field)
    141: 99,   # Toronto Blue Jays (Rogers Centre)
    120: 101,  # Washington Nationals (Nationals Park)
}

# Informasi detail stadion
STADIUM_INFO = {
    109: {"name": "Chase Field", "city": "Phoenix", "type": "Retractable", "capacity": 48405, "dims": {"LF": 330, "CF": 407, "RF": 335}},
    144: {"name": "Truist Park", "city": "Atlanta", "type": "Outdoor", "capacity": 41084, "dims": {"LF": 335, "CF": 400, "RF": 325}},
    110: {"name": "Oriole Park at Camden Yards", "city": "Baltimore", "type": "Outdoor", "capacity": 45971, "dims": {"LF": 333, "CF": 400, "RF": 318}},
    111: {"name": "Fenway Park", "city": "Boston", "type": "Outdoor", "capacity": 37755, "dims": {"LF": 310, "CF": 390, "RF": 302}},
    112: {"name": "Wrigley Field", "city": "Chicago", "type": "Outdoor", "capacity": 41649, "dims": {"LF": 355, "CF": 400, "RF": 353}},
    145: {"name": "Guaranteed Rate Field", "city": "Chicago", "type": "Outdoor", "capacity": 40615, "dims": {"LF": 330, "CF": 400, "RF": 335}},
    113: {"name": "Great American Ball Park", "city": "Cincinnati", "type": "Outdoor", "capacity": 42319, "dims": {"LF": 328, "CF": 404, "RF": 325}},
    114: {"name": "Progressive Field", "city": "Cleveland", "type": "Outdoor", "capacity": 34830, "dims": {"LF": 325, "CF": 400, "RF": 325}},
    115: {"name": "Coors Field", "city": "Denver", "type": "Outdoor", "capacity": 50144, "dims": {"LF": 347, "CF": 415, "RF": 350}},
    116: {"name": "Comerica Park", "city": "Detroit", "type": "Outdoor", "capacity": 41083, "dims": {"LF": 342, "CF": 412, "RF": 330}},
    117: {"name": "Minute Maid Park", "city": "Houston", "type": "Retractable", "capacity": 41168, "dims": {"LF": 315, "CF": 409, "RF": 326}},
    118: {"name": "Kauffman Stadium", "city": "Kansas City", "type": "Outdoor", "capacity": 37903, "dims": {"LF": 330, "CF": 410, "RF": 330}},
    108: {"name": "Angel Stadium", "city": "Anaheim", "type": "Outdoor", "capacity": 45517, "dims": {"LF": 330, "CF": 400, "RF": 330}},
    119: {"name": "Dodger Stadium", "city": "Los Angeles", "type": "Outdoor", "capacity": 56000, "dims": {"LF": 330, "CF": 400, "RF": 330}},
    146: {"name": "loanDepot park", "city": "Miami", "type": "Retractable", "capacity": 36742, "dims": {"LF": 344, "CF": 400, "RF": 335}},
    158: {"name": "American Family Field", "city": "Milwaukee", "type": "Retractable", "capacity": 41900, "dims": {"LF": 344, "CF": 400, "RF": 345}},
    142: {"name": "Target Field", "city": "Minneapolis", "type": "Outdoor", "capacity": 38544, "dims": {"LF": 339, "CF": 404, "RF": 328}},
    121: {"name": "Citi Field", "city": "New York", "type": "Outdoor", "capacity": 41922, "dims": {"LF": 335, "CF": 408, "RF": 330}},
    147: {"name": "Yankee Stadium", "city": "New York", "type": "Outdoor", "capacity": 46537, "dims": {"LF": 318, "CF": 408, "RF": 314}},
    133: {"name": "Oakland Coliseum", "city": "Oakland", "type": "Outdoor", "capacity": 46847, "dims": {"LF": 330, "CF": 400, "RF": 330}},
    143: {"name": "Citizens Bank Park", "city": "Philadelphia", "type": "Outdoor", "capacity": 42792, "dims": {"LF": 329, "CF": 401, "RF": 330}},
    134: {"name": "PNC Park", "city": "Pittsburgh", "type": "Outdoor", "capacity": 38747, "dims": {"LF": 325, "CF": 399, "RF": 320}},
    135: {"name": "Petco Park", "city": "San Diego", "type": "Outdoor", "capacity": 40209, "dims": {"LF": 334, "CF": 396, "RF": 322}},
    137: {"name": "Oracle Park", "city": "San Francisco", "type": "Outdoor", "capacity": 41265, "dims": {"LF": 339, "CF": 391, "RF": 309}},
    136: {"name": "T-Mobile Park", "city": "Seattle", "type": "Retractable", "capacity": 47929, "dims": {"LF": 331, "CF": 401, "RF": 326}},
    138: {"name": "Busch Stadium", "city": "St. Louis", "type": "Outdoor", "capacity": 45494, "dims": {"LF": 336, "CF": 400, "RF": 335}},
    139: {"name": "Tropicana Field", "city": "St. Petersburg", "type": "Indoor", "capacity": 25000, "dims": {"LF": 315, "CF": 404, "RF": 322}},
    140: {"name": "Globe Life Field", "city": "Arlington", "type": "Retractable", "capacity": 40300, "dims": {"LF": 329, "CF": 407, "RF": 326}},
    141: {"name": "Rogers Centre", "city": "Toronto", "type": "Retractable", "capacity": 41500, "dims": {"LF": 328, "CF": 400, "RF": 328}},
    120: {"name": "Nationals Park", "city": "Washington", "type": "Outdoor", "capacity": 41339, "dims": {"LF": 337, "CF": 402, "RF": 335}},
}

def get_park_factor(team_id):
    """
    Mengambil nilai Park Factor untuk tim/stadion tertentu.
    
    Args:
        team_id (int): ID tim MLB.
        
    Returns:
        int: Nilai park factor (default 100 jika tidak ditemukan).
    """
    return PARK_FACTORS.get(team_id, 100)

def classify_park(park_factor):
    """
    Mengklasifikasikan stadion berdasarkan nilai park factor.
    
    Args:
        park_factor (int): Nilai park factor.
        
    Returns:
        str: "HITTERS_PARK", "PITCHERS_PARK", atau "NEUTRAL".
    """
    if park_factor > 105:
        return "HITTERS_PARK"
    elif park_factor < 95:
        return "PITCHERS_PARK"
    else:
        return "NEUTRAL"

# Catatan Khusus: Coors Field (ID: 115)
# Ketinggian Denver (5.280 kaki) membuat udara tipis, mengurangi hambatan bola.
# Hal ini menyebabkan bola terbang lebih jauh dan break pitcher berkurang.
# Meskipun dimensinya luas (CF 415'), Coors tetap menjadi stadion paling ramah hitter.
