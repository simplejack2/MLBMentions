"""Venue / ballpark mention probability model.

Base rate: ~55% per game (venue-specific references appear in ~half of broadcasts).

Venue markets are typically broadcast-mention markets: "Will the announcer
reference [park name / ballpark feature] during today's game?"

Key drivers:
- Iconic / distinctive parks (Fenway, Wrigley, Coors) get mentioned more often
- First game of a series at a new venue → more context-setting mentions
- Night games / weekend games have larger audiences → more colour commentary
"""

from __future__ import annotations

# Known high-mention venues (abbreviation → mention boost in log-odds units)
_ICONIC_VENUE_BOOST: dict[str, float] = {
    "BOS": 0.55,   # Fenway Park — Green Monster always discussed
    "CHC": 0.50,   # Wrigley Field — ivy, history
    "COL": 0.45,   # Coors Field — altitude constantly referenced
    "NYY": 0.40,   # Yankee Stadium — Monument Park, short porch
    "SFG": 0.35,   # Oracle Park — McCovey Cove
    "PIT": 0.30,   # PNC Park — river, bridges
    "BAL": 0.25,   # Camden Yards — classic park
    "LAD": 0.20,   # Dodger Stadium — history, views
    "STL": 0.15,   # Busch Stadium — Gateway Arch backdrop
    "NYM": 0.10,   # Citi Field — Shea references
}

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class VenueModel(FamilyModel):
    BASE_RATE = 0.55
    DESCRIPTION = "P(venue/ballpark mentioned by broadcaster | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0

        # Iconic venue bonus
        home_abbr = ctx.home_abbr.upper()
        score += _ICONIC_VENUE_BOOST.get(home_abbr, 0.0)

        # High-scoring, exciting games generate more in-depth commentary
        score += (ctx.run_factor - 1.0) * 0.60

        return score
