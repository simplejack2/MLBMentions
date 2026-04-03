"""Static park factor tables for MLB venues.

Factors are relative to league average (1.00 = perfectly neutral).
Values > 1.0 favour the event; < 1.0 suppress it.

Sources: multi-year park factor history (Baseball Reference, Fangraphs).
These are stable priors — update annually or when a park changes dimensions.
"""

from __future__ import annotations

# Home-run park factors by team abbreviation (home park).
# These feed grand_slam and bases_loaded models.
HR_FACTOR: dict[str, float] = {
    "CIN": 1.28,   # Great American Ball Park — very hitter-friendly
    "COL": 1.22,   # Coors Field — altitude, thin air
    "PHI": 1.18,   # Citizens Bank Park
    "BOS": 1.15,   # Fenway Park
    "HOU": 1.13,   # Minute Maid Park — Crawford Boxes in left
    "NYY": 1.12,   # Yankee Stadium — short right-field porch
    "BAL": 1.11,   # Camden Yards
    "TEX": 1.10,   # Globe Life Field
    "MIL": 1.08,   # American Family Field
    "LAD": 1.07,   # Dodger Stadium
    "TOR": 1.05,   # Rogers Centre
    "DET": 1.04,   # Comerica Park
    "ATL": 1.03,   # Truist Park
    "CHC": 1.02,   # Wrigley Field (wind-adjusted neutral)
    "MIN": 1.01,   # Target Field
    "WSN": 1.00,   # Nationals Park
    "STL": 0.99,   # Busch Stadium
    "NYM": 0.98,   # Citi Field
    "ARI": 0.97,   # Chase Field
    "TBR": 0.96,   # Tropicana Field
    "CLE": 0.96,   # Progressive Field
    "SFG": 0.95,   # Oracle Park — marine layer
    "KCR": 0.95,   # Kauffman Stadium
    "CWS": 0.94,   # Guaranteed Rate Field
    "SEA": 0.93,   # T-Mobile Park — marine layer
    "MIA": 0.93,   # LoanDepot Park
    "PIT": 0.92,   # PNC Park
    "LAA": 0.91,   # Angel Stadium
    "OAK": 0.90,   # Oakland Coliseum
    "SDP": 0.89,   # Petco Park — classic pitcher's park
    "TB":  0.96,   # alias for TBR
    "KC":  0.95,   # alias for KCR
    "SD":  0.89,   # alias for SDP
    "SF":  0.95,   # alias for SFG
    "WSH": 1.00,   # alias for WSN
}

# Triple factors: large outfields + artificial turf inflate triple rates.
TRIPLE_FACTOR: dict[str, float] = {
    "COL": 1.45,   # Coors Field — enormous outfield
    "PIT": 1.30,   # PNC Park — deep gaps
    "MIA": 1.25,   # LoanDepot Park — deep alleys
    "MIL": 1.20,   # American Family Field — turf
    "TBR": 1.18,   # Tropicana Field — turf
    "TOR": 1.15,   # Rogers Centre — turf
    "MIN": 1.12,   # Target Field
    "SDP": 1.10,   # Petco Park — deep outfield
    "SEA": 1.08,   # T-Mobile Park
    "ARI": 1.05,   # Chase Field
    "KCR": 1.05,   # Kauffman Stadium — fast turf-like surface
    "DET": 1.03,   # Comerica Park
    "BAL": 1.02,   # Camden Yards
    "CLE": 1.00,
    "STL": 1.00,
    "CHC": 0.98,
    "WSN": 0.97,
    "NYM": 0.96,
    "LAD": 0.95,
    "CWS": 0.95,
    "PHI": 0.95,
    "ATL": 0.97,
    "TEX": 1.00,
    "SFG": 0.90,   # Oracle Park — marine layer keeps ball in park
    "BOS": 0.90,   # Fenway — Green Monster turns triples into doubles
    "HOU": 0.92,
    "LAA": 0.98,
    "NYY": 0.93,   # Short porch → HR park, not triple park
    "CIN": 0.95,
    "OAK": 1.00,
    "TB":  1.18,
    "KC":  1.05,
    "SD":  1.10,
    "SF":  0.90,
    "WSH": 0.97,
}

# Run environment factor (overall scoring context).
# Feeds bases_loaded model — high-scoring parks = more baserunners.
RUN_FACTOR: dict[str, float] = {
    "COL": 1.35,
    "CIN": 1.18,
    "PHI": 1.12,
    "BOS": 1.10,
    "NYY": 1.09,
    "HOU": 1.08,
    "TEX": 1.07,
    "MIL": 1.06,
    "BAL": 1.05,
    "LAD": 1.04,
    "TOR": 1.03,
    "DET": 1.02,
    "ATL": 1.02,
    "CHC": 1.01,
    "MIN": 1.00,
    "STL": 0.99,
    "NYM": 0.98,
    "ARI": 0.97,
    "WSN": 0.97,
    "CLE": 0.96,
    "TBR": 0.96,
    "KCR": 0.95,
    "CWS": 0.95,
    "PIT": 0.94,
    "MIA": 0.93,
    "LAA": 0.93,
    "SFG": 0.92,
    "SEA": 0.91,
    "SDP": 0.90,
    "OAK": 0.90,
    "TB":  0.96,
    "KC":  0.95,
    "SD":  0.90,
    "SF":  0.92,
    "WSH": 0.97,
}


def get_hr_factor(team_abbr: str) -> float:
    """Return HR park factor for the home team, defaulting to 1.0."""
    return HR_FACTOR.get(team_abbr.upper(), 1.0)


def get_triple_factor(team_abbr: str) -> float:
    """Return triple park factor for the home team, defaulting to 1.0."""
    return TRIPLE_FACTOR.get(team_abbr.upper(), 1.0)


def get_run_factor(team_abbr: str) -> float:
    """Return overall run environment factor, defaulting to 1.0."""
    return RUN_FACTOR.get(team_abbr.upper(), 1.0)
