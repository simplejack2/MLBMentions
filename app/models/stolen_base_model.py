"""Stolen base probability model.

Base rate: ~72% per game (at least one stolen base attempt in ~72% of games).

Key drivers: team speed (SB rate), pitcher hold tendency (BB9 proxy), catcher.
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class StolenBaseModel(FamilyModel):
    BASE_RATE = 0.72
    DESCRIPTION = "P(stolen base attempt | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0
        score += ctx.home_offense.speed_score * 1.00
        score += ctx.away_offense.speed_score * 1.00
        # Walk-prone pitchers give more baserunners → more steal opportunities
        score += ctx.home_pitcher.bb9_delta * 0.30
        score += ctx.away_pitcher.bb9_delta * 0.30
        # Patient offenses draw more walks = more first-base opportunities to run
        score += ctx.home_offense.walk_rate_delta * 0.20
        score += ctx.away_offense.walk_rate_delta * 0.20
        return score
