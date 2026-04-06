"""Match Kalshi market titles to specific MLB games.

Strategy
--------
1. Build a token→abbreviation map for all 30 MLB teams.
2. Normalise the market title (lower, strip punctuation).
3. Score each game: +2 per unambiguous team token found in the title.
4. Return the best-matching game if its score reaches the threshold.

The threshold of 2 requires at least one clear team token match — a single
ambiguous city word (e.g. "Milwaukee" alone from a multi-sport parlay) won't
reach the bar because those markets should have been rejected by the MLB
classifier before they get here.
"""

from __future__ import annotations

import re

from app.schemas.game import Game
from app.schemas.market import Market

# All known team name tokens (lower-case) → canonical abbreviation.
_TEAM_TOKENS: dict[str, str] = {
    # Arizona Diamondbacks
    "arizona": "ARI", "diamondbacks": "ARI", "dbacks": "ARI", "ari": "ARI",
    # Atlanta Braves
    "atlanta": "ATL", "braves": "ATL", "atl": "ATL",
    # Baltimore Orioles
    "baltimore": "BAL", "orioles": "BAL", "bal": "BAL",
    # Boston Red Sox
    "boston": "BOS", "redsox": "BOS", "bos": "BOS",
    # Chicago Cubs
    "cubs": "CHC", "chc": "CHC",
    # Chicago White Sox
    "whitesox": "CWS", "cws": "CWS",
    # Cincinnati Reds
    "cincinnati": "CIN", "reds": "CIN", "cin": "CIN",
    # Cleveland Guardians
    "cleveland": "CLE", "guardians": "CLE", "cle": "CLE",
    # Colorado Rockies
    "colorado": "COL", "rockies": "COL", "col": "COL",
    # Detroit Tigers
    "detroit": "DET", "tigers": "DET", "det": "DET",
    # Houston Astros
    "houston": "HOU", "astros": "HOU", "hou": "HOU",
    # Kansas City Royals
    "kansas": "KCR", "royals": "KCR", "kcr": "KCR", "kc": "KCR",
    # Los Angeles Angels
    "angels": "LAA", "laa": "LAA", "anaheim": "LAA",
    # Los Angeles Dodgers
    "dodgers": "LAD", "lad": "LAD",
    # Miami Marlins
    "miami": "MIA", "marlins": "MIA", "mia": "MIA",
    # Milwaukee Brewers
    "milwaukee": "MIL", "brewers": "MIL", "mil": "MIL",
    # Minnesota Twins
    "minnesota": "MIN", "twins": "MIN", "min": "MIN",
    # New York Mets
    "mets": "NYM", "nym": "NYM",
    # New York Yankees
    "yankees": "NYY", "yanks": "NYY", "nyy": "NYY",
    # Oakland / Sacramento Athletics
    "oakland": "OAK", "athletics": "OAK", "oak": "OAK", "sac": "OAK",
    # Philadelphia Phillies
    "philadelphia": "PHI", "phillies": "PHI", "phi": "PHI",
    # Pittsburgh Pirates
    "pittsburgh": "PIT", "pirates": "PIT", "pit": "PIT",
    # San Diego Padres
    "padres": "SDP", "sdp": "SDP", "sd": "SDP",
    # San Francisco Giants
    "giants": "SFG", "sfg": "SFG", "sf": "SFG",
    # Seattle Mariners
    "seattle": "SEA", "mariners": "SEA", "sea": "SEA",
    # St. Louis Cardinals
    "louis": "STL", "cardinals": "STL", "stl": "STL", "cards": "STL",
    # Tampa Bay Rays
    "tampa": "TBR", "rays": "TBR", "tbr": "TBR", "tb": "TBR",
    # Texas Rangers
    "texas": "TEX", "rangers": "TEX", "tex": "TEX",
    # Toronto Blue Jays
    "toronto": "TOR", "jays": "TOR", "bluejays": "TOR", "tor": "TOR",
    # Washington Nationals
    "washington": "WSN", "nationals": "WSN", "wsn": "WSN", "wsh": "WSN", "nats": "WSN",
    # Generic "chicago" — could be Cubs or White Sox; resolved by scoring
    "chicago": "_CHI",
}

# Minimum score to consider a market matched to a game.
# Score of 2 = one clear team token matched.
_MATCH_THRESHOLD = 2


def match_market_to_game(market: Market, games: list[Game]) -> Game | None:
    """Return the best-matching game for this market, or None."""
    if not games:
        return None

    haystack = _normalize(f"{market.title} {market.subtitle or ''} {market.rules_primary or ''}")

    best_game: Game | None = None
    best_score = 0

    for game in games:
        score = _score_game(haystack, game)
        if score > best_score:
            best_score = score
            best_game = game

    return best_game if best_score >= _MATCH_THRESHOLD else None


def _score_game(haystack: str, game: Game) -> int:
    score = 0
    game_abbrs = {
        (game.home_team.abbreviation or "").upper(),
        (game.away_team.abbreviation or "").upper(),
    }

    for token, abbr in _TEAM_TOKENS.items():
        if abbr == "_CHI":
            if "chicago" in haystack:
                if "cubs" in haystack and "CHC" in game_abbrs:
                    score += 2
                elif ("white" in haystack or "sox" in haystack) and "CWS" in game_abbrs:
                    score += 2
                elif "CHC" in game_abbrs or "CWS" in game_abbrs:
                    score += 1
            continue

        if token in haystack and abbr in game_abbrs:
            score += 2

    # Fallback: match team name words for cities not in the token map
    for word in game.team_names_lower:
        if len(word) > 3 and word in haystack:
            score += 1

    return score


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
